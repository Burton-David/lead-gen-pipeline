"""Asynchronous web crawler.

Fetches pages over HTTPX by default and, when a page needs JavaScript rendering, over a
headless Playwright/Chromium browser. The crawler honours robots.txt, rate-limits per
domain, retries transient failures with exponential backoff, and flags likely CAPTCHA
challenge pages. Playwright is an optional dependency: the HTTPX path works without it,
and a clear error is raised only if a browser fetch is requested while it is missing.
"""

from __future__ import annotations

import asyncio
import random
import urllib.robotparser
from collections import OrderedDict
from typing import Any
from urllib.parse import urlparse

import httpx

try:
    from playwright.async_api import (
        Browser,
        Page,
        async_playwright,
    )
    from playwright.async_api import (
        Error as PlaywrightBaseError,
    )
    from playwright.async_api import (
        Response as PlaywrightResponse,
    )
    from playwright.async_api import (
        TimeoutError as PlaywrightTimeoutError,
    )

    PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without the browser extra
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None  # type: ignore[assignment]
    Browser = Page = PlaywrightResponse = None  # type: ignore[assignment, misc]

    class PlaywrightBaseError(Exception):  # type: ignore[no-redef]
        """Fallback so ``except PlaywrightBaseError`` is safe without Playwright."""

    class PlaywrightTimeoutError(PlaywrightBaseError):  # type: ignore[no-redef]
        """Fallback timeout error mirroring Playwright's hierarchy."""


try:
    from .config import settings as global_app_settings
    from .utils import (
        async_retry,
        clean_text,
        domain_rate_limiter,
        extract_domain,
        logger,
    )
except ImportError:
    from lead_gen_pipeline.config import settings as global_app_settings  # type: ignore
    from lead_gen_pipeline.utils import (  # type: ignore
        async_retry,
        clean_text,
        domain_rate_limiter,
        extract_domain,
        logger,
    )


class RobotsTxtDisallowedError(Exception):
    """Raised when a URL is disallowed by robots.txt."""

    def __init__(self, url: str, user_agent: str) -> None:
        self.url = url
        self.user_agent = user_agent
        super().__init__(
            f"URL '{url}' is disallowed by robots.txt for user-agent '{user_agent}'."
        )


class PlaywrightNotInstalledError(RuntimeError):
    """Raised when a browser fetch is requested but Playwright is not installed."""

    def __init__(self) -> None:
        super().__init__(
            "Playwright is required for browser-based fetching. Install it with "
            "`pip install 'lead-gen-pipeline[browser]'` then "
            "`playwright install chromium`."
        )


class AsyncWebCrawler:
    """Async page fetcher: robots.txt enforcement, per-domain rate limiting, retries.

    Uses HTTPX by default and Playwright/Chromium for JavaScript-rendered pages. The
    Playwright browser and the robots.txt cache are shared at the class level.
    """

    _playwright_instance: Any = None
    _browser: Browser | None = None
    _class_logger = logger

    def __init__(self) -> None:
        self.settings = global_app_settings.crawler
        self.app_settings = global_app_settings
        self.logger = self._class_logger
        self.domain_rate_limiter = domain_rate_limiter

        # LRU cache of parsed robots.txt files, with a per-domain lock so the same
        # robots.txt is never fetched concurrently by two coroutines.
        self._robots_parsers_cache: OrderedDict[
            str, urllib.robotparser.RobotFileParser | None
        ] = OrderedDict()
        self._robots_fetch_locks: dict[str, asyncio.Lock] = {}
        self._registry_lock: asyncio.Lock = asyncio.Lock()
        self.logger.info(
            f"Crawler ready. robots.txt respect: {self.settings.RESPECT_ROBOTS_TXT}"
        )

    def _construct_headers(self, url: str) -> dict[str, str]:
        return {
            "User-Agent": self.settings.USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
                "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "DNT": "1",
        }

    async def _fetch_and_parse_robots_txt(
        self, domain: str
    ) -> urllib.robotparser.RobotFileParser | None:
        """Fetch robots.txt for a domain (HTTPS then HTTP) and parse it."""
        if not domain:
            self.logger.warning("Attempted to fetch robots.txt for an empty domain.")
            return None

        robots_content: str | None = None
        final_robots_url_fetched: str | None = None
        robots_fetch_headers = {"User-Agent": self.settings.USER_AGENT}

        async with httpx.AsyncClient(
            timeout=self.settings.ROBOTS_TXT_FETCH_TIMEOUT_SECONDS,
            follow_redirects=True,
            verify=True,
        ) as client:
            for scheme in ("https", "http"):
                robots_url = f"{scheme}://{domain}/robots.txt"
                try:
                    self.logger.debug(f"Fetching robots.txt from: {robots_url}")
                    response = await client.get(
                        robots_url, headers=robots_fetch_headers
                    )
                    if response.status_code == 200:
                        robots_content = response.text
                        final_robots_url_fetched = str(response.url)
                        self.logger.info(f"Fetched robots.txt for {domain}")
                        break
                    elif response.status_code == 404:
                        self.logger.debug(
                            f"robots.txt not found at {robots_url} (404)."
                        )
                    else:
                        self.logger.warning(
                            f"robots.txt {robots_url} -> {response.status_code}"
                        )
                except httpx.RequestError as e:
                    self.logger.warning(
                        f"RequestError fetching robots.txt from {robots_url}: "
                        f"{type(e).__name__} - {e}"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Unexpected error fetching robots.txt from {robots_url}: "
                        f"{type(e).__name__} - {e}"
                    )
                if robots_content:
                    break

        if robots_content:
            parser = urllib.robotparser.RobotFileParser()
            try:
                parser.parse(robots_content.splitlines())
                return parser
            except Exception as e:
                self.logger.error(
                    f"Error parsing robots.txt for {domain} from "
                    f"{final_robots_url_fetched or '?'}: {e}. Assuming permissive."
                )
                return None

        self.logger.debug(f"No valid robots.txt for {domain}. Assuming permissive.")
        return None

    async def _get_robots_parser(
        self, domain: str
    ) -> urllib.robotparser.RobotFileParser | None:
        """Return a parsed robots.txt for the domain, using the LRU cache."""
        if not domain:
            return None

        if domain in self._robots_parsers_cache:
            self._robots_parsers_cache.move_to_end(domain)
            self.logger.trace(f"Using cached robots.txt parser for: {domain}")
            return self._robots_parsers_cache[domain]

        async with self._registry_lock:
            if domain not in self._robots_fetch_locks:
                self._robots_fetch_locks[domain] = asyncio.Lock()

        async with self._robots_fetch_locks[domain]:
            # Re-check the cache now that we hold the per-domain lock.
            if domain in self._robots_parsers_cache:
                self._robots_parsers_cache.move_to_end(domain)
                return self._robots_parsers_cache[domain]

            self.logger.debug(f"Fetching robots.txt for uncached domain: {domain}")
            parser = await self._fetch_and_parse_robots_txt(domain)

            if len(self._robots_parsers_cache) >= self.settings.ROBOTS_TXT_CACHE_SIZE:
                oldest_domain, _ = self._robots_parsers_cache.popitem(last=False)
                self.logger.debug(f"Robots.txt cache full; evicted: {oldest_domain}")

            self._robots_parsers_cache[domain] = parser
            return parser

    async def _check_robots_txt(self, url: str) -> None:
        """Raise :class:`RobotsTxtDisallowedError` if the URL is disallowed."""
        domain = extract_domain(url)
        if not domain:
            self.logger.warning(
                f"No domain from '{url}' for robots.txt check; assuming allowed."
            )
            return

        user_agent = self.settings.USER_AGENT
        parser = await self._get_robots_parser(domain)

        if parser is None:
            self.logger.debug(
                f"No robots.txt parser for '{domain}'. Assuming permissive for: {url}"
            )
            return

        try:
            is_allowed = parser.can_fetch(user_agent, url)
        except Exception as e:
            self.logger.error(
                f"robots.txt can_fetch() failed for {url} (UA: {user_agent}): {e}. "
                "Assuming permissive."
            )
            return

        if not is_allowed:
            self.logger.warning(
                f"'{url}' disallowed by robots.txt for UA '{user_agent}'."
            )
            raise RobotsTxtDisallowedError(url, user_agent)
        self.logger.debug(f"URL '{url}' allowed by robots.txt for '{user_agent}'.")

    @classmethod
    async def _ensure_playwright_browser(cls) -> Browser:
        """Ensure a Playwright browser is running and return it."""
        if not PLAYWRIGHT_AVAILABLE:
            raise PlaywrightNotInstalledError()

        if cls._playwright_instance is None:
            cls._class_logger.info("Starting Playwright instance...")
            try:
                cls._playwright_instance = await async_playwright().start()
            except Exception as e:
                cls._class_logger.critical(
                    f"Failed to start Playwright instance: {e}", exc_info=True
                )
                raise

        if cls._browser is None or not cls._browser.is_connected():
            cls._class_logger.info("Launching Playwright browser (Chromium)...")
            launch_options: dict[str, Any] = {
                "headless": global_app_settings.crawler.PLAYWRIGHT_HEADLESS_MODE,
                "args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-infobars",
                    "--disable-popup-blocking",
                    "--disable-notifications",
                    "--ignore-certificate-errors",
                    "--disable-features=site-per-process",
                ],
            }
            proxy_url = (
                global_app_settings.crawler.HTTP_PROXY_URL
                or global_app_settings.crawler.HTTPS_PROXY_URL
            )
            if proxy_url:
                parsed_proxy = urlparse(str(proxy_url))
                proxy_config: dict[str, str] = {
                    "server": f"{parsed_proxy.scheme}://{parsed_proxy.netloc}"
                }
                if parsed_proxy.username:
                    proxy_config["username"] = parsed_proxy.username
                if parsed_proxy.password:
                    proxy_config["password"] = parsed_proxy.password
                launch_options["proxy"] = proxy_config

            try:
                cls._browser = await cls._playwright_instance.chromium.launch(
                    **launch_options
                )
            except Exception as e:
                cls._class_logger.critical(
                    f"Failed to launch Playwright browser: {e}", exc_info=True
                )
                raise
        return cls._browser

    async def _get_playwright_page(self) -> tuple[Page, Any]:
        """Create and configure a fresh Playwright page and context."""
        browser = await self._ensure_playwright_browser()
        viewport_width = random.randint(1280, 1920)
        viewport_height = random.randint(720, 1080)

        context = await browser.new_context(
            user_agent=self.settings.USER_AGENT,
            viewport={"width": viewport_width, "height": viewport_height},
            java_script_enabled=True,
            bypass_csp=True,
        )
        page = await context.new_page()
        self.logger.debug(
            f"New Playwright page. Viewport: {viewport_width}x{viewport_height}"
        )
        return page, context

    @classmethod
    async def close_playwright_resources(cls) -> None:
        """Close the Playwright browser and instance if running."""
        if cls._browser and cls._browser.is_connected():
            cls._class_logger.info("Closing Playwright browser...")
            await cls._browser.close()
            cls._browser = None
        if cls._playwright_instance:
            cls._class_logger.info("Stopping Playwright instance...")
            await cls._playwright_instance.stop()
            cls._playwright_instance = None

    async def _fetch_with_playwright(
        self, url: str, timeout_ms: int
    ) -> tuple[str, int, str]:
        """Fetch a page with Playwright; return (html, status_code, final_url)."""
        self.logger.debug(f"Playwright fetch for: {url} (timeout {timeout_ms}ms)")
        context: Any | None = None
        html_content = ""
        status_code = 0
        final_url = url

        try:
            page, context = await self._get_playwright_page()
            response: PlaywrightResponse | None = await page.goto(
                url, wait_until="domcontentloaded", timeout=timeout_ms
            )
            if response:
                status_code = response.status
                html_content = await page.content()
                final_url = page.url
                if 200 <= status_code < 300:
                    self.logger.success(
                        f"Fetched (Playwright) {final_url} (Status: {status_code})"
                    )
                else:
                    self.logger.warning(
                        f"Playwright {final_url}: non-2xx status {status_code}"
                    )
            else:
                self.logger.error(
                    f"Playwright navigation to {url} returned no response."
                )
                status_code = 599
                raise PlaywrightBaseError(
                    f"Playwright navigation to {url} failed to "
                    "return a response object."
                )
        except PlaywrightTimeoutError as e:
            self.logger.error(f"Playwright TimeoutError for {url}: {str(e)[:200]}")
            status_code = 408
            raise
        except PlaywrightBaseError as e:
            self.logger.error(
                f"PlaywrightBaseError for {url}: {type(e).__name__} - {str(e)[:200]}"
            )
            if not status_code:
                status_code = 598
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected Playwright error for {url}: {type(e).__name__}",
                exc_info=True,
            )
            raise PlaywrightBaseError(
                f"Unexpected error in Playwright operation for {url}: {e}"
            ) from e
        finally:
            if context:
                try:
                    await context.close()
                except Exception as e:
                    self.logger.error(
                        f"Error closing Playwright context for {url}: {e}"
                    )

        return html_content, status_code, final_url

    async def _perform_httpx_fetch_attempt(
        self, url: str, headers: dict[str, str], proxy: str | None = None
    ) -> tuple[str, int, str]:
        """Perform a single HTTPX GET; return (html, status_code, final_url)."""
        client_kwargs: dict[str, Any] = {
            "headers": headers,
            "timeout": self.settings.DEFAULT_TIMEOUT_SECONDS,
            "follow_redirects": True,
            "verify": True,
        }
        if proxy:
            client_kwargs["proxy"] = proxy
            self.logger.debug(f"HTTPX using proxy: {proxy}")

        async with httpx.AsyncClient(**client_kwargs) as client:
            self.logger.info(f"HTTPX fetch for: {url}")
            response = await client.get(url)
            final_url = str(response.url)
            status_code = response.status_code
            response.raise_for_status()  # 4xx/5xx -> retried by async_retry
            self.logger.success(f"Fetched (HTTPX) {final_url} (Status: {status_code})")
            return response.text, status_code, final_url

    @async_retry(
        # Retry transient fetch failures only. A robots.txt disallow will not change
        # on retry, so it is excluded and surfaces immediately.
        exceptions=(
            httpx.HTTPStatusError,
            httpx.TimeoutException,
            httpx.RequestError,
            PlaywrightBaseError,
        ),
        retry_logger=logger,
    )
    async def fetch_page_content_with_retry(
        self, url: str, use_playwright: bool
    ) -> tuple[str, int, str]:
        """Fetch page content with retry, rate limiting, and robots.txt enforcement."""
        if self.settings.RESPECT_ROBOTS_TXT:
            await self._check_robots_txt(url)

        headers = self._construct_headers(url)
        proxy: str | None = None
        proxy_setting = self.settings.HTTPS_PROXY_URL or self.settings.HTTP_PROXY_URL
        if proxy_setting:
            proxy = str(proxy_setting)

        domain_for_limit = extract_domain(url)
        if not domain_for_limit:
            raise ValueError(f"Cannot extract domain for rate limiting from URL: {url}")

        async with await self.domain_rate_limiter.wait_for_domain(domain_for_limit):
            if use_playwright:
                self.logger.info(f"Fetching (Playwright) with rate limit for {url}")
                playwright_timeout_ms = self.settings.DEFAULT_TIMEOUT_SECONDS * 1000 * 2
                html_content, status_code, final_url = (
                    await self._fetch_with_playwright(
                        url, timeout_ms=playwright_timeout_ms
                    )
                )
            else:
                self.logger.info(f"Fetching (HTTPX) with rate limit for {url}")
                html_content, status_code, final_url = (
                    await self._perform_httpx_fetch_attempt(url, headers, proxy)
                )

        if html_content:
            sample = clean_text(html_content[:2500])
            if sample:
                sample = sample.lower()
                captcha_keywords = (
                    "captcha",
                    "are you a robot",
                    "verify you're human",
                    "recaptcha",
                    "hcaptcha",
                    "turnstile",
                )
                if any(keyword in sample for keyword in captcha_keywords):
                    self.logger.warning(
                        f"Potential CAPTCHA detected on {final_url}. "
                        "Content might be a challenge page."
                    )

        return html_content, status_code, final_url

    async def fetch_page(
        self, url: str, use_playwright: bool | None = None
    ) -> tuple[str | None, int, str]:
        """Fetch a page, returning (html_or_None, status_code, final_url).

        Network and policy failures are mapped to status codes rather than raised, so
        callers can react uniformly: 403 for robots.txt-disallowed, 408 for timeouts,
        598 for Playwright errors, 599 for HTTPX request errors, 500 for the unexpected.
        """
        if not url or not url.startswith(("http://", "https://")):
            self.logger.error(f"Invalid URL format: {url}. Must start with http(s)://.")
            return None, 0, url

        if not extract_domain(url):
            self.logger.error(f"Could not extract domain from URL: {url}")
            return None, 0, url

        should_use_playwright = (
            use_playwright
            if use_playwright is not None
            else self.settings.USE_PLAYWRIGHT_BY_DEFAULT
        )

        try:
            return await self.fetch_page_content_with_retry(url, should_use_playwright)
        except RobotsTxtDisallowedError as e:
            self.logger.error(
                f"RobotsTxtDisallowed: '{e.url}' blocked for UA '{e.user_agent}'."
            )
            return None, 403, e.url
        except httpx.HTTPStatusError as e:
            self.logger.error(
                f"HTTPStatusError for {url}: Status {e.response.status_code}"
            )
            return None, e.response.status_code, str(e.request.url)
        except httpx.TimeoutException as e:
            self.logger.error(f"HTTPX TimeoutException for {url}: {e}")
            return None, 408, url
        except httpx.RequestError as e:
            self.logger.error(f"HTTPX RequestError for {url}: {type(e).__name__} - {e}")
            final_exc_url = str(e.request.url) if getattr(e, "request", None) else url
            return None, 599, final_exc_url
        except PlaywrightBaseError as e:
            self.logger.error(
                f"PlaywrightBaseError for {url}: {type(e).__name__} - {str(e)[:200]}"
            )
            return None, 598, url
        except RuntimeError as e:
            self.logger.opt(exception=True).critical(
                f"Unexpected RuntimeError during fetch for {url}: {e}"
            )
            return None, 500, url
        except Exception as e:
            self.logger.opt(exception=True).critical(
                f"Unexpected error during fetch for {url}: {type(e).__name__} - {e}"
            )
            return None, 500, url

    async def close(self) -> None:
        """Close crawler resources and clear caches."""
        self.logger.info("AsyncWebCrawler.close(): releasing resources...")
        await self.close_playwright_resources()
        async with self._registry_lock:
            self._robots_parsers_cache.clear()
            self._robots_fetch_locks.clear()
        self.logger.info("Robots.txt cache and fetch locks cleared.")
