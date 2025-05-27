# lead_gen_pipeline/crawler.py
# Version: 2025-05-23 16:55 EDT
import httpx
import asyncio
import random
from typing import Optional, Tuple, Dict, Any, cast
from urllib.parse import urlparse, urlunparse, urljoin
import urllib.robotparser
from collections import OrderedDict # For LRU cache

# Playwright imports
from playwright.async_api import (
    async_playwright,
    Browser,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    Error as PlaywrightBaseError,
    Response as PlaywrightResponse
)

try:
    from .config import settings as global_app_settings
    from .utils import logger, async_retry, domain_rate_limiter, extract_domain, clean_text
except ImportError:
    from lead_gen_pipeline.config import settings as global_app_settings # type: ignore
    from lead_gen_pipeline.utils import logger, async_retry, domain_rate_limiter, extract_domain, clean_text # type: ignore

# Custom exception for robots.txt disallow
class RobotsTxtDisallowedError(Exception):
    """Raised when a URL is disallowed by robots.txt."""
    def __init__(self, url: str, user_agent: str):
        self.url = url
        self.user_agent = user_agent
        super().__init__(f"URL '{url}' is disallowed for user-agent '{user_agent}' by robots.txt.")

class AsyncWebCrawler:
    _playwright_instance = None
    _browser: Optional[Browser] = None
    logger_class = logger

    def __init__(self):
        self.settings = global_app_settings.crawler
        self.app_settings = global_app_settings
        self.logger = logger
        self.domain_rate_limiter = domain_rate_limiter
        self._robots_parsers_cache: OrderedDict[str, urllib.robotparser.RobotFileParser] = OrderedDict()
        self._robots_fetch_locks: Dict[str, asyncio.Lock] = {}

    def _get_random_user_agent(self) -> str:
        if self.settings.USER_AGENTS:
            return random.choice(self.settings.USER_AGENTS)
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def _construct_headers(self, url: str) -> Dict[str, str]:
        headers = {
            "User-Agent": self._get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
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
        parsed_url = urlparse(url)
        if parsed_url.netloc:
            headers["Referer"] = "https://www.google.com/"
        return headers

    async def _fetch_and_parse_robots_txt(self, domain: str) -> Optional[urllib.robotparser.RobotFileParser]:
        robots_url_https = f"https://{domain}/robots.txt"
        robots_url_http = f"http://{domain}/robots.txt"
        robots_content: Optional[str] = None
        final_robots_url_tried = robots_url_https
        robots_fetch_headers = {"User-Agent": self._get_random_user_agent()}

        async with httpx.AsyncClient(timeout=self.settings.ROBOTS_TXT_FETCH_TIMEOUT_SECONDS, follow_redirects=True) as client:
            try:
                self.logger.debug(f"Attempting to fetch robots.txt from: {robots_url_https}")
                response = await client.get(robots_url_https, headers=robots_fetch_headers)
                final_robots_url_tried = str(response.url)
                if response.status_code == 200:
                    robots_content = response.text
                elif response.status_code == 404:
                    self.logger.debug(f"robots.txt not found at {robots_url_https} (404).")
                else:
                    self.logger.warning(f"Failed to fetch robots.txt from {robots_url_https} with status {response.status_code}. Trying HTTP.")
                    final_robots_url_tried = robots_url_http
                    response = await client.get(robots_url_http, headers=robots_fetch_headers)
                    final_robots_url_tried = str(response.url)
                    if response.status_code == 200:
                        robots_content = response.text
                    else:
                        self.logger.warning(f"Failed to fetch robots.txt from {robots_url_http} as well (status: {response.status_code}). Assuming permissive.")
                        return None
            except httpx.RequestError as e:
                self.logger.warning(f"Error fetching robots.txt from {final_robots_url_tried}: {type(e).__name__}. Assuming permissive. Error: {e}")
                return None

        if robots_content:
            parser = urllib.robotparser.RobotFileParser()
            try:
                parser.parse(robots_content.splitlines())
                self.logger.info(f"Successfully fetched and parsed robots.txt for domain: {domain} from {final_robots_url_tried}")
                return parser
            except Exception as e:
                self.logger.error(f"Error parsing robots.txt content for {domain}: {e}. Assuming permissive.")
                return None
        
        self.logger.debug(f"No robots.txt content found or fetched for {domain}. Assuming permissive.")
        return None

    async def _get_robots_parser(self, domain: str) -> Optional[urllib.robotparser.RobotFileParser]:
        if domain in self._robots_parsers_cache:
            self._robots_parsers_cache.move_to_end(domain)
            self.logger.trace(f"Using cached robots.txt parser for domain: {domain}")
            return self._robots_parsers_cache[domain]

        if domain not in self._robots_fetch_locks:
            self._robots_fetch_locks[domain] = asyncio.Lock()
        
        async with self._robots_fetch_locks[domain]:
            if domain in self._robots_parsers_cache:
                self._robots_parsers_cache.move_to_end(domain)
                return self._robots_parsers_cache[domain]

            parser = await self._fetch_and_parse_robots_txt(domain)
            
            if len(self._robots_parsers_cache) >= self.settings.ROBOTS_TXT_CACHE_SIZE:
                oldest_domain, _ = self._robots_parsers_cache.popitem(last=False)
                self.logger.debug(f"Robots.txt cache full. Removed parser for domain: {oldest_domain}")
            
            self._robots_parsers_cache[domain] = cast(urllib.robotparser.RobotFileParser, parser)
            self.logger.debug(f"Cached robots.txt parser (or None) for domain: {domain}. Cache size: {len(self._robots_parsers_cache)}")
            return parser

    async def _check_robots_txt(self, url: str) -> None:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        if not domain:
            self.logger.warning(f"Could not extract domain from URL '{url}' for robots.txt check.")
            return

        user_agent_for_robots = self.settings.ROBOTS_TXT_USER_AGENT
        self.logger.debug(f"Checking robots.txt for URL: {url} with UA: {user_agent_for_robots}")

        parser = await self._get_robots_parser(domain)

        if parser:
            is_allowed: bool
            try:
                # This call to can_fetch itself should not raise RobotsTxtDisallowedError
                is_allowed = parser.can_fetch(user_agent_for_robots, url)
            except Exception as e: # Catch any unexpected error from can_fetch() itself
                self.logger.error(f"Unexpected error during robots.txt parser.can_fetch() for {url} with UA {user_agent_for_robots}: {e}. Assuming permissive.")
                return # Assume permissive on unexpected parser error

            if not is_allowed:
                self.logger.warning(f"URL '{url}' is disallowed by robots.txt for user-agent '{user_agent_for_robots}'.")
                raise RobotsTxtDisallowedError(url, user_agent_for_robots) # This is the intended exception
            else:
                self.logger.debug(f"URL '{url}' is allowed by robots.txt for user-agent '{user_agent_for_robots}'.")
        else:
            self.logger.debug(f"No valid robots.txt parser for domain '{domain}'. Assuming permissive for URL: {url}")

    @classmethod
    async def _ensure_playwright_browser(cls) -> Browser:
        if cls._playwright_instance is None:
            cls.logger_class.info("Starting Playwright instance...")
            cls._playwright_instance = await async_playwright().start()
            cls.logger_class.info("Playwright instance started.")

        if cls._browser is None or not cls._browser.is_connected():
            cls.logger_class.info("Launching new Playwright browser (Chromium)...")
            browser_launch_options: Dict[str, Any] = {
                "headless": global_app_settings.crawler.PLAYWRIGHT_HEADLESS_MODE,
                "args": [
                    '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled', '--disable-infobars',
                    '--disable-popup-blocking', '--disable-notifications',
                    '--ignore-certificate-errors',
                ]
            }
            proxy_to_use = None
            if global_app_settings.crawler.HTTP_PROXY_URL:
                parsed_proxy = urlparse(str(global_app_settings.crawler.HTTP_PROXY_URL))
                proxy_server_url = f"{parsed_proxy.scheme}://{parsed_proxy.hostname}:{parsed_proxy.port}"
                proxy_to_use = {"server": proxy_server_url}
                if parsed_proxy.username: proxy_to_use["username"] = parsed_proxy.username
                if parsed_proxy.password: proxy_to_use["password"] = parsed_proxy.password
                cls.logger_class.info(f"Playwright will use proxy: {proxy_server_url} (auth redacted if present)")
            
            if proxy_to_use:
                browser_launch_options["proxy"] = proxy_to_use

            cls._browser = await cls._playwright_instance.chromium.launch(**browser_launch_options)
            cls.logger_class.info("Playwright browser (Chromium) launched.")
        return cls._browser

    async def _get_playwright_page(self) -> Tuple[Page, Any]:
        browser = await self._ensure_playwright_browser()
        viewport_width = random.randint(1280, 1920)
        viewport_height = random.randint(720, 1080)
        context = await browser.new_context(
            user_agent=self._get_random_user_agent(),
            viewport={"width": viewport_width, "height": viewport_height},
            java_script_enabled=True, bypass_csp=True,
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await context.new_page()
        self.logger.debug(f"New Playwright page created with UA: {await page.evaluate('navigator.userAgent')}, Viewport: {viewport_width}x{viewport_height}")
        return page, context

    @classmethod
    async def close_playwright_resources(cls):
        if cls._browser and cls._browser.is_connected():
            cls.logger_class.info("Closing Playwright browser...")
            await cls._browser.close()
            cls._browser = None
            cls.logger_class.info("Playwright browser closed.")
        if cls._playwright_instance:
            cls.logger_class.info("Stopping Playwright instance...")
            await cls._playwright_instance.stop()
            cls._playwright_instance = None
            cls.logger_class.info("Playwright instance stopped.")

    async def _fetch_with_playwright(self, url: str, timeout_ms: int) -> Tuple[str, int, str]:
        self.logger.debug(f"Attempting Playwright fetch for: {url} with timeout {timeout_ms}ms")
        page: Optional[Page] = None
        context: Optional[Any] = None 
        html_content: str = ""
        status_code: int = 0 
        final_url: str = url

        try:
            page, context = await self._get_playwright_page()
            response: Optional[PlaywrightResponse] = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=timeout_ms
            )
            if response:
                status_code = response.status
                html_content = await page.content()
                final_url = page.url
                if 200 <= status_code < 300:
                    self.logger.success(f"Successfully fetched (Playwright) {final_url} with status {status_code}")
                else:
                    self.logger.warning(f"Fetched (Playwright) {final_url} with status {status_code}")
            else:
                self.logger.error(f"Playwright navigation to {url} returned no response object.")
                status_code = 599 
                raise PlaywrightBaseError(f"Playwright navigation to {url} failed to return a response object.")
        except PlaywrightTimeoutError as e:
            self.logger.error(f"Playwright TimeoutError for {url} after {timeout_ms}ms: {str(e)[:200]}")
            raise 
        except PlaywrightBaseError as e: 
            self.logger.error(f"PlaywrightBaseError for {url}: {type(e).__name__} - {str(e)[:200]}")
            raise 
        except Exception as e: 
            self.logger.error(f"Unexpected error during Playwright fetch for {url}: {type(e).__name__} - {str(e)[:200]}")
            status_code = 597 
            raise PlaywrightBaseError(f"Unexpected error in Playwright operation for {url}: {e}") from e
        finally:
            if context:
                try:
                    await context.close()
                    self.logger.debug(f"Playwright context for {url} closed.")
                except Exception as e:
                    self.logger.error(f"Error closing Playwright context for {url}: {e}")
        return html_content, status_code, final_url

    async def _perform_httpx_fetch_attempt(
        self, url: str, headers: Dict[str, str], proxies: Optional[Dict[str, str]] = None
    ) -> Tuple[str, int, str]:
        client_kwargs: Dict[str, Any] = {
            "headers": headers, "timeout": self.settings.DEFAULT_TIMEOUT_SECONDS,
            "follow_redirects": True, "verify": True
        }
        if proxies: client_kwargs["proxies"] = proxies
        async with httpx.AsyncClient(**client_kwargs) as client:
            self.logger.info(f"Attempting HTTPX fetch for: {url}")
            response = await client.get(url)
            final_url = str(response.url)
            status_code = response.status_code
            response.raise_for_status() 
            html_content = response.text
            self.logger.success(f"Successfully fetched (HTTPX) {final_url} with status {status_code}")
            return html_content, status_code, final_url

    @async_retry(exceptions=(httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError, PlaywrightBaseError, RobotsTxtDisallowedError, RuntimeError))
    async def fetch_page_content(
        self, url: str, use_playwright: bool
    ) -> Tuple[str, int, str]:
        
        if self.settings.RESPECT_ROBOTS_TXT:
            await self._check_robots_txt(url) 

        headers = self._construct_headers(url)
        proxies_dict: Optional[Dict[str, str]] = None
        if self.settings.HTTP_PROXY_URL:
            proxies_dict = {
                "http://": str(self.settings.HTTP_PROXY_URL),
                "https": str(self.settings.HTTPS_PROXY_URL) if self.settings.HTTPS_PROXY_URL else str(self.settings.HTTP_PROXY_URL)
            }
        
        html_content: str = ""
        status_code: int = 0
        final_url: str = url

        async with await self.domain_rate_limiter.wait_for_domain(extract_domain(url)):
            if use_playwright:
                self.logger.info(f"Fetching (Playwright) for {url}")
                playwright_timeout_ms = self.settings.DEFAULT_TIMEOUT_SECONDS * 1000 * 2
                html_content, status_code, final_url = await self._fetch_with_playwright(url, timeout_ms=playwright_timeout_ms)
            else: 
                html_content, status_code, final_url = await self._perform_httpx_fetch_attempt(url, headers, proxies_dict)
        
        if html_content:
            cleaned_text_for_captcha_check = clean_text(html_content[:2000].lower())
            if cleaned_text_for_captcha_check and any(
                keyword in cleaned_text_for_captcha_check for keyword in ["captcha", "are you a robot", "verify you're human", "recaptcha"]
            ):
                self.logger.warning(f"Potential CAPTCHA detected on {final_url}. Content might be a challenge page.")
        
        return html_content, status_code, final_url

    async def fetch_page(
        self, url: str, use_playwright: Optional[bool] = None
    ) -> Tuple[Optional[str], int, str]:
        domain = extract_domain(url)
        if not domain:
            self.logger.error(f"Invalid URL or could not extract domain: {url}")
            return None, 0, url 

        should_use_playwright = use_playwright if use_playwright is not None else self.settings.USE_PLAYWRIGHT_BY_DEFAULT
        
        try:
            html_content, status_code, final_url = await self.fetch_page_content(url, should_use_playwright)
            return html_content, status_code, final_url
        except RobotsTxtDisallowedError as e:
            self.logger.error(f"FETCH_PAGE_FINAL: RobotsTxtDisallowedError for {e.url} with UA '{e.user_agent}'. Not fetched.")
            return None, 403, e.url 
        except httpx.HTTPStatusError as e:
            self.logger.error(f"FETCH_PAGE_FINAL: HTTPStatusError for {url} (final: {str(e.request.url)}): Status {e.response.status_code}")
            return None, e.response.status_code, str(e.request.url)
        except httpx.TimeoutException as e:
            self.logger.error(f"FETCH_PAGE_FINAL: TimeoutException for {url}: {e}")
            return None, 408, url 
        except httpx.RequestError as e: 
            self.logger.error(f"FETCH_PAGE_FINAL: RequestError for {url}: {type(e).__name__} - {e}")
            final_exc_url = str(e.request.url) if hasattr(e, 'request') and e.request else url
            return None, 599, final_exc_url 
        except PlaywrightBaseError as e: 
            self.logger.error(f"FETCH_PAGE_FINAL: PlaywrightBaseError for {url}: {type(e).__name__} - {str(e)[:200]}")
            return None, 598, url 
        except RuntimeError as e: 
            self.logger.opt(exception=True).critical(f"FETCH_PAGE_FINAL: Unexpected RuntimeError for {url}: {e}")
            return None, 500, url
        except Exception as e:
            self.logger.opt(exception=True).critical(f"FETCH_PAGE_FINAL: Truly unexpected error for {url}: {e}")
            return None, 500, url

    async def close(self):
        self.logger.info("AsyncWebCrawler close() called.")
        await self.close_playwright_resources()
        self._robots_parsers_cache.clear()
        self._robots_fetch_locks.clear()
        self.logger.info("Robots.txt cache and fetch locks cleared.")

