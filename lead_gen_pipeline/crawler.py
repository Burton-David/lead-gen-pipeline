# lead_gen_pipeline/crawler.py
# Version: Gemini-2025-05-26 22:05 EDT
import httpx
import asyncio
import random
from typing import Optional, Tuple, Dict, Any, cast
from urllib.parse import urlparse, urlunparse, urljoin
import urllib.robotparser
from collections import OrderedDict # For LRU cache

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
    # Fallback for scenarios where relative imports might fail (e.g. running script directly)
    from lead_gen_pipeline.config import settings as global_app_settings # type: ignore
    from lead_gen_pipeline.utils import logger, async_retry, domain_rate_limiter, extract_domain, clean_text # type: ignore

# Custom exception for robots.txt disallow
class RobotsTxtDisallowedError(Exception):
    """Raised when a URL is disallowed by robots.txt."""
    def __init__(self, url: str, user_agent: str):
        self.url = url
        self.user_agent = user_agent
        super().__init__(f"URL '{url}' is disallowed by robots.txt for user-agent '{user_agent}'.")

class AsyncWebCrawler:
    _playwright_instance = None
    _browser: Optional[Browser] = None
    # Class attribute for logger, initialized from utils.
    # This ensures that even if multiple instances of AsyncWebCrawler are made (they shouldn't be typically),
    # they share the same logger configuration from utils.py.
    _class_logger = logger 

    def __init__(self):
        self.settings = global_app_settings.crawler
        self.app_settings = global_app_settings # For accessing other settings like MAX_RETRIES
        self.logger = self._class_logger # Use the shared logger
        self.domain_rate_limiter = domain_rate_limiter # Use the global rate limiter instance
        
        # LRU cache for robots.txt parsers
        self._robots_parsers_cache: OrderedDict[str, Optional[urllib.robotparser.RobotFileParser]] = OrderedDict()
        # Locks to prevent concurrent fetching of the same robots.txt file
        self._robots_fetch_locks: Dict[str, asyncio.Lock] = {}
        self.logger.info(f"AsyncWebCrawler initialized. Robots.txt respect: {self.settings.RESPECT_ROBOTS_TXT}")

    def _get_random_user_agent(self) -> str:
        """Selects a random User-Agent string from the configured list."""
        if self.settings.USER_AGENTS:
            return random.choice(self.settings.USER_AGENTS)
        # Fallback default User-Agent if list is empty (should not happen with Pydantic defaults)
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def _construct_headers(self, url: str) -> Dict[str, str]:
        """Constructs a dictionary of headers for HTTP requests."""
        headers = {
            "User-Agent": self._get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br", # Modern browsers support Brotli (br)
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1", # Signal to servers that we prefer HTTPS
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none", # For initial requests; could be "cross-site" or "same-origin" for subsequent
            "Sec-Fetch-User": "?1", # Indicates user-initiated request
            "DNT": "1", # Do Not Track header
        }
        # Add a Referer. A common generic referer can sometimes help.
        # More sophisticated referer spoofing could be added later based on navigation context.
        headers["Referer"] = "https://www.google.com/" 
        return headers

    async def _fetch_and_parse_robots_txt(self, domain: str) -> Optional[urllib.robotparser.RobotFileParser]:
        """Fetches robots.txt for a domain, trying HTTPS then HTTP, and parses it."""
        if not domain:
            self.logger.warning("Attempted to fetch robots.txt for an empty domain.")
            return None

        schemes_to_try = ["https", "http"]
        robots_content: Optional[str] = None
        final_robots_url_fetched: Optional[str] = None

        robots_fetch_headers = {"User-Agent": self.settings.ROBOTS_TXT_USER_AGENT} # Use specific UA for robots.txt
        
        # Create a short-lived client for fetching robots.txt
        # Timeouts and retries for robots.txt fetching are handled by its own settings.
        async with httpx.AsyncClient(
            timeout=self.settings.ROBOTS_TXT_FETCH_TIMEOUT_SECONDS, 
            follow_redirects=True,
            verify=True # Standard SSL verification
        ) as client:
            for scheme in schemes_to_try:
                robots_url = f"{scheme}://{domain}/robots.txt"
                try:
                    self.logger.debug(f"Attempting to fetch robots.txt from: {robots_url}")
                    response = await client.get(robots_url, headers=robots_fetch_headers)
                    
                    if response.status_code == 200:
                        robots_content = response.text
                        final_robots_url_fetched = str(response.url)
                        self.logger.info(f"Successfully fetched robots.txt for domain: {domain} from {final_robots_url_fetched}")
                        break # Found and fetched
                    elif response.status_code == 404:
                        self.logger.debug(f"robots.txt not found at {robots_url} (status 404).")
                        # If HTTPS 404, we will try HTTP. If HTTP 404, we stop.
                    else:
                        self.logger.warning(f"Failed to fetch robots.txt from {robots_url} with status {response.status_code}.")
                except httpx.RequestError as e:
                    self.logger.warning(f"RequestError fetching robots.txt from {robots_url}: {type(e).__name__} - {e}")
                except Exception as e: # Catch any other unexpected errors
                    self.logger.error(f"Unexpected error fetching robots.txt from {robots_url}: {type(e).__name__} - {e}")
                
                if robots_content: # Stop if successfully fetched
                    break
            
        if robots_content:
            parser = urllib.robotparser.RobotFileParser()
            try:
                parser.parse(robots_content.splitlines())
                return parser
            except Exception as e:
                self.logger.error(f"Error parsing robots.txt content for {domain} from {final_robots_url_fetched or 'unknown URL'}: {e}. Assuming permissive.")
                return None # Parsing failed, treat as no robots.txt
        
        self.logger.debug(f"No valid robots.txt content found or fetched for {domain}. Assuming permissive.")
        return None # No content fetched or other error

    async def _get_robots_parser(self, domain: str) -> Optional[urllib.robotparser.RobotFileParser]:
        """Retrieves a parsed robots.txt file, using a cache or fetching if necessary."""
        if not domain: return None

        # Check cache first (thread-safe due to OrderedDict's nature for single-threaded async access)
        if domain in self._robots_parsers_cache:
            self._robots_parsers_cache.move_to_end(domain) # Mark as recently used for LRU
            self.logger.trace(f"Using cached robots.txt parser for domain: {domain}")
            return self._robots_parsers_cache[domain]

        # Get or create a lock for this specific domain to prevent multiple concurrent fetches
        # of the same robots.txt file.
        async with self._registry_lock: # Protect access to _robots_fetch_locks dict
            if domain not in self._robots_fetch_locks:
                self._robots_fetch_locks[domain] = asyncio.Lock()
        
        domain_fetch_lock = self._robots_fetch_locks[domain]
        async with domain_fetch_lock:
            # Double-check cache after acquiring lock, in case another coroutine populated it.
            if domain in self._robots_parsers_cache:
                self._robots_parsers_cache.move_to_end(domain)
                return self._robots_parsers_cache[domain]

            self.logger.debug(f"Fetching robots.txt for domain (not in cache): {domain}")
            parser = await self._fetch_and_parse_robots_txt(domain)
            
            # Add to cache, maintaining LRU policy
            if len(self._robots_parsers_cache) >= self.settings.ROBOTS_TXT_CACHE_SIZE:
                oldest_domain, _ = self._robots_parsers_cache.popitem(last=False) # Remove oldest
                self.logger.debug(f"Robots.txt cache full ({self.settings.ROBOTS_TXT_CACHE_SIZE} items). Removed parser for domain: {oldest_domain}")
            
            self._robots_parsers_cache[domain] = parser 
            self.logger.debug(f"Cached robots.txt parser (or None) for domain: {domain}. Cache size: {len(self._robots_parsers_cache)}")
            return parser

    async def _check_robots_txt(self, url: str) -> None:
        """Checks if a URL is allowed by robots.txt, raising RobotsTxtDisallowedError if not."""
        domain = extract_domain(url)
        if not domain:
            self.logger.warning(f"Could not extract domain from URL '{url}' for robots.txt check. Assuming allowed.")
            return

        user_agent_for_robots = self.settings.ROBOTS_TXT_USER_AGENT
        self.logger.debug(f"Checking robots.txt for URL: {url} with UA: {user_agent_for_robots}")

        parser = await self._get_robots_parser(domain)

        if parser:
            is_allowed = False # Default to not allowed if can_fetch fails unexpectedly
            try:
                is_allowed = parser.can_fetch(user_agent_for_robots, url)
            except Exception as e: 
                self.logger.error(f"Unexpected error during robots.txt parser.can_fetch() for {url} (UA: {user_agent_for_robots}): {e}. Assuming permissive on this error.")
                return # If parser itself errors, assume permissive for this check to avoid blocking valid URLs

            if not is_allowed:
                self.logger.warning(f"URL '{url}' is disallowed by robots.txt for user-agent '{user_agent_for_robots}'.")
                raise RobotsTxtDisallowedError(url, user_agent_for_robots)
            else:
                self.logger.debug(f"URL '{url}' is allowed by robots.txt for user-agent '{user_agent_for_robots}'.")
        else:
            self.logger.debug(f"No valid robots.txt parser for domain '{domain}'. Assuming permissive for URL: {url}")

    @classmethod
    async def _ensure_playwright_browser(cls) -> Browser:
        """Ensures Playwright instance and browser are initialized and returns the browser."""
        if cls._playwright_instance is None:
            cls._class_logger.info("Starting Playwright instance...")
            try:
                cls._playwright_instance = await async_playwright().start()
                cls._class_logger.info("Playwright instance started.")
            except Exception as e:
                cls._class_logger.critical(f"Failed to start Playwright instance: {e}", exc_info=True)
                raise # Cannot continue without playwright if it's needed

        if cls._browser is None or not cls._browser.is_connected():
            cls._class_logger.info("Launching new Playwright browser (Chromium)...")
            browser_launch_options: Dict[str, Any] = {
                "headless": global_app_settings.crawler.PLAYWRIGHT_HEADLESS_MODE,
                "args": [ # Common arguments to try and make Playwright less detectable
                    '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled', '--disable-infobars',
                    '--disable-popup-blocking', '--disable-notifications',
                    '--ignore-certificate-errors', '--disable-features=site-per-process', # Added site-per-process disable
                    # Further args could be added for stealth, e.g., related to WebGL, canvas, fonts
                ]
            }
            # Configure proxy for Playwright if specified in settings
            proxy_url = global_app_settings.crawler.HTTP_PROXY_URL or global_app_settings.crawler.HTTPS_PROXY_URL
            if proxy_url:
                parsed_proxy = urlparse(str(proxy_url))
                proxy_server_url = f"{parsed_proxy.scheme}://{parsed_proxy.netloc}" #scheme, hostname, port
                proxy_config = {"server": proxy_server_url}
                if parsed_proxy.username: proxy_config["username"] = parsed_proxy.username
                if parsed_proxy.password: proxy_config["password"] = parsed_proxy.password
                browser_launch_options["proxy"] = proxy_config
                cls._class_logger.info(f"Playwright will use proxy: {proxy_server_url} (auth redacted if used)")
            
            try:
                cls._browser = await cls._playwright_instance.chromium.launch(**browser_launch_options)
                cls._class_logger.info("Playwright browser (Chromium) launched.")
            except Exception as e:
                cls._class_logger.critical(f"Failed to launch Playwright browser: {e}", exc_info=True)
                raise
        return cls._browser

    async def _get_playwright_page(self) -> Tuple[Page, Any]: # 'Any' is for the context type
        """Creates and configures a new Playwright page and context."""
        browser = await self._ensure_playwright_browser()
        
        # Randomize viewport for better stealth
        viewport_width = random.randint(1280, 1920)
        viewport_height = random.randint(720, 1080)
        
        context = await browser.new_context(
            user_agent=self._get_random_user_agent(), # Rotate UA per context
            viewport={"width": viewport_width, "height": viewport_height},
            java_script_enabled=True,
            bypass_csp=True, # Can help with some sites, but use with caution
            # Other context options for stealth: timezone, locale, geolocation, permissions
        )
        # Anti-detection script: tries to hide 'webdriver' property
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await context.new_page()
        self.logger.debug(f"New Playwright page created. UA: {await page.evaluate('navigator.userAgent')}, Viewport: {viewport_width}x{viewport_height}")
        return page, context

    @classmethod
    async def close_playwright_resources(cls):
        """Closes the Playwright browser and instance if they exist."""
        if cls._browser and cls._browser.is_connected():
            cls._class_logger.info("Closing Playwright browser...")
            await cls._browser.close()
            cls._browser = None
            cls._class_logger.info("Playwright browser closed.")
        if cls._playwright_instance:
            cls._class_logger.info("Stopping Playwright instance...")
            # playwright.stop() is synchronous, but we are in an async context.
            # The `await self._playwright_instance.stop()` was based on some examples,
            # but if `stop()` is not awaitable, this should be handled differently.
            # For `async_playwright`, `stop()` is indeed async.
            await cls._playwright_instance.stop()
            cls._playwright_instance = None
            cls._class_logger.info("Playwright instance stopped.")

    async def _fetch_with_playwright(self, url: str, timeout_ms: int) -> Tuple[str, int, str]:
        """Fetches a page using Playwright, returning HTML, status code, and final URL."""
        self.logger.debug(f"Attempting Playwright fetch for: {url} with timeout {timeout_ms}ms")
        page: Optional[Page] = None
        context: Optional[Any] = None 
        html_content: str = ""
        status_code: int = 0 # Default to 0 indicating an issue before response
        final_url: str = url

        try:
            page, context = await self._get_playwright_page()
            response: Optional[PlaywrightResponse] = await page.goto(
                url,
                wait_until="domcontentloaded", # 'load' or 'networkidle' can be used for JS-heavy sites
                timeout=timeout_ms
            )
            if response:
                status_code = response.status
                html_content = await page.content()
                final_url = page.url # URL after any redirects
                if 200 <= status_code < 300:
                    self.logger.success(f"Successfully fetched (Playwright) {final_url} (Status: {status_code})")
                else:
                    self.logger.warning(f"Fetched (Playwright) {final_url} but with non-2xx status: {status_code}")
            else:
                # This case (no response object) should ideally be rare with Playwright's goto
                self.logger.error(f"Playwright navigation to {url} returned no response object.")
                status_code = 599 # Custom status for "no response object from Playwright"
                raise PlaywrightBaseError(f"Playwright navigation to {url} failed to return a response object.")
        
        except PlaywrightTimeoutError as e:
            self.logger.error(f"Playwright TimeoutError for {url} after {timeout_ms}ms: {str(e)[:200]}")
            status_code = 408 # Standard HTTP Timeout
            raise # Re-raise to be caught by async_retry or caller
        except PlaywrightBaseError as e: # Catch other Playwright-specific errors
            self.logger.error(f"PlaywrightBaseError for {url}: {type(e).__name__} - {str(e)[:200]}")
            if not status_code: status_code = 598 # Custom for other Playwright errors
            raise
        except Exception as e: # Catch any other unexpected errors
            self.logger.error(f"Unexpected error during Playwright fetch for {url}: {type(e).__name__} - {str(e)[:200]}", exc_info=True)
            if not status_code: status_code = 597 # Custom for unexpected errors in PW fetch
            # Wrap in PlaywrightBaseError to ensure it's handled by retry logic if needed
            raise PlaywrightBaseError(f"Unexpected error in Playwright operation for {url}: {e}") from e
        finally:
            if context:
                try:
                    await context.close()
                    self.logger.debug(f"Playwright context for {url} closed.")
                except Exception as e: # Log error but don't let it overshadow primary exception
                    self.logger.error(f"Error closing Playwright context for {url}: {e}")
            # Page is closed when context is closed.

        return html_content, status_code, final_url

    async def _perform_httpx_fetch_attempt(
        self, url: str, headers: Dict[str, str], proxies: Optional[Dict[str, str]] = None
    ) -> Tuple[str, int, str]:
        """Performs a single HTTPX fetch attempt."""
        # httpx_client should be created per request or managed with limits for keep-alive
        # For simplicity here, creating per request. In a high-volume scenario, a shared client with limits is better.
        client_kwargs: Dict[str, Any] = {
            "headers": headers, 
            "timeout": self.settings.DEFAULT_TIMEOUT_SECONDS,
            "follow_redirects": True, 
            "verify": True # Enable SSL verification by default
        }
        if proxies: 
            client_kwargs["proxies"] = proxies
            self.logger.debug(f"HTTPX using proxies: {proxies.get('http://', proxies.get('https://'))}")

        async with httpx.AsyncClient(**client_kwargs) as client:
            self.logger.info(f"Attempting HTTPX fetch for: {url}")
            response = await client.get(url)
            final_url = str(response.url) # URL after redirects
            status_code = response.status_code
            
            # This will raise HTTPStatusError for 4xx/5xx, caught by async_retry
            response.raise_for_status() 
            
            html_content = response.text # Assuming text content
            self.logger.success(f"Successfully fetched (HTTPX) {final_url} (Status: {status_code})")
            return html_content, status_code, final_url

    @async_retry( # Uses global_app_settings.crawler.MAX_RETRIES and .BACKOFF_FACTOR by default
        exceptions=(httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError, PlaywrightBaseError, RobotsTxtDisallowedError, RuntimeError),
        retry_logger=logger # Pass the shared logger instance
    )
    async def fetch_page_content_with_retry( # Renamed to reflect retry is included
        self, url: str, use_playwright: bool
    ) -> Tuple[str, int, str]: # html_content, status_code, final_url
        """
        Internal method to fetch page content, applying retry logic.
        This is the method decorated by @async_retry.
        """
        if self.settings.RESPECT_ROBOTS_TXT:
            await self._check_robots_txt(url) # This can raise RobotsTxtDisallowedError

        headers = self._construct_headers(url)
        proxies_dict: Optional[Dict[str, str]] = None
        if self.settings.HTTP_PROXY_URL: # Assuming same proxy for HTTP/HTTPS if only HTTP_PROXY_URL is set
            http_proxy = str(self.settings.HTTP_PROXY_URL)
            https_proxy = str(self.settings.HTTPS_PROXY_URL) if self.settings.HTTPS_PROXY_URL else http_proxy
            proxies_dict = {"http://": http_proxy, "https://": https_proxy}
        
        html_content: str = ""
        status_code: int = 0
        final_url: str = url

        # Acquire domain rate limit permit
        domain_for_limit = extract_domain(url)
        if not domain_for_limit: # Should not happen if URL validation is done prior
             raise ValueError(f"Cannot extract domain for rate limiting from URL: {url}")

        async with await self.domain_rate_limiter.wait_for_domain(domain_for_limit):
            if use_playwright:
                self.logger.info(f"Fetching (Playwright) with rate limit for {url}")
                # Playwright timeout can be longer as it involves browser interactions
                playwright_timeout_ms = self.settings.DEFAULT_TIMEOUT_SECONDS * 1000 * 2 # e.g., 60s if default is 30s
                html_content, status_code, final_url = await self._fetch_with_playwright(url, timeout_ms=playwright_timeout_ms)
            else: 
                self.logger.info(f"Fetching (HTTPX) with rate limit for {url}")
                html_content, status_code, final_url = await self._perform_httpx_fetch_attempt(url, headers, proxies_dict)
        
        # Basic CAPTCHA detection (can be significantly enhanced)
        if html_content:
            # Use a smaller portion of text for quick check, convert to lower for case-insensitivity
            text_sample_for_captcha_check = clean_text(html_content[:2500]) # Check first 2500 chars
            if text_sample_for_captcha_check:
                 text_sample_for_captcha_check = text_sample_for_captcha_check.lower()
                 captcha_keywords = ["captcha", "are you a robot", "verify you're human", "recaptcha", "hcaptcha", "turnstile"]
                 if any(keyword in text_sample_for_captcha_check for keyword in captcha_keywords):
                    self.logger.warning(f"Potential CAPTCHA detected on {final_url}. Content might be a challenge page.")
        
        return html_content, status_code, final_url

    async def fetch_page(
        self, url: str, use_playwright: Optional[bool] = None
    ) -> Tuple[Optional[str], int, str]: # html_content, status_code, final_url
        """
        Public method to fetch a page. Handles URL validation, determines fetch strategy,
        and manages exceptions from the fetching process.
        """
        if not url or not url.startswith(('http://', 'https://')):
            self.logger.error(f"Invalid URL format: {url}. Must start with http:// or https://.")
            return None, 0, url # 0 status for invalid URL format

        domain = extract_domain(url)
        if not domain: # Further validation by extract_domain
            self.logger.error(f"Invalid URL or could not extract domain: {url}")
            return None, 0, url 

        # Determine if Playwright should be used for this specific URL
        should_use_playwright = use_playwright if use_playwright is not None else self.settings.USE_PLAYWRIGHT_BY_DEFAULT
        
        try:
            # Call the method that has the @async_retry decorator
            html_content, status_code, final_url = await self.fetch_page_content_with_retry(url, should_use_playwright)
            return html_content, status_code, final_url
        except RobotsTxtDisallowedError as e:
            self.logger.error(f"RobotsTxtDisallowed: URL '{e.url}' is blocked by robots.txt for UA '{e.user_agent}'.")
            return None, 403, e.url # HTTP 403 Forbidden
        except httpx.HTTPStatusError as e: # Typically 4xx/5xx client/server errors from HTTPX
            self.logger.error(f"HTTPStatusError for {url} (final: {str(e.request.url)}): Status {e.response.status_code}")
            return None, e.response.status_code, str(e.request.url)
        except httpx.TimeoutException as e:
            self.logger.error(f"HTTPX TimeoutException for {url}: {e}")
            return None, 408, url # HTTP 408 Request Timeout
        except httpx.RequestError as e: # Other HTTPX network-related errors (DNS, connection, etc.)
            self.logger.error(f"HTTPX RequestError for {url}: {type(e).__name__} - {e}")
            final_exc_url = str(e.request.url) if hasattr(e, 'request') and e.request else url
            return None, 599, final_exc_url # Custom for general request errors
        except PlaywrightBaseError as e: # Includes PlaywrightTimeoutError and other PW errors
            self.logger.error(f"PlaywrightBaseError for {url}: {type(e).__name__} - {str(e)[:200]}")
            # Status code might have been set within _fetch_with_playwright, otherwise use a custom one
            # For simplicity, using a generic Playwright error status if not more specific.
            return None, 598, url # Custom for Playwright errors
        except RuntimeError as e: # Catch unexpected RuntimeErrors from retry logic or elsewhere
            self.logger.opt(exception=True).critical(f"Unexpected RuntimeError during fetch for {url}: {e}")
            return None, 500, url # Internal Server Error
        except Exception as e: # Catch-all for any other truly unexpected exceptions
            self.logger.opt(exception=True).critical(f"Unexpected general error during fetch for {url}: {type(e).__name__} - {e}")
            return None, 500, url

    async def close(self):
        """Closes crawler resources, including Playwright and clearing caches."""
        self.logger.info("AsyncWebCrawler close() called. Closing resources...")
        await self.close_playwright_resources() # Ensure Playwright is shut down
        
        async with self._registry_lock: # Protect shared cache/lock dictionaries
            self._robots_parsers_cache.clear()
            self._robots_fetch_locks.clear()
        self.logger.info("Robots.txt cache and fetch locks cleared.")
        self.logger.info("AsyncWebCrawler resources closed.")

    # Required for _get_robots_parser to access _registry_lock if it's not already an instance var
    # It seems _registry_lock was added in utils.py for DomainRateLimiter but not here.
    # Let's add it for crawler's internal lock management consistency.
    def __post_init__(self): # Pydantic v2 style post-init
         self._registry_lock: asyncio.Lock = asyncio.Lock()
