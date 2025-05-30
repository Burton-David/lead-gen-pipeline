# lead_gen_pipeline/utils.py
# Version: 2025-05-22 20:45 UTC (with make_absolute_url fix)
import sys
import asyncio
import random
import time
import re
from functools import wraps
from typing import Optional, Callable, Any, Coroutine, List
from urllib.parse import urlparse, urljoin
import tldextract

from loguru import logger

try:
    from .config import LoggingSettings, AppSettings, settings as global_app_settings
except ImportError:
    # This fallback should ideally not be hit if the package is structured and run correctly.
    # For robustness in various execution contexts, we keep it.
    from lead_gen_pipeline.config import LoggingSettings, AppSettings, settings as global_app_settings # type: ignore


def setup_logger(custom_logging_settings: Optional[LoggingSettings] = None) -> logger:
    """
    Configures and returns the Loguru logger instance.
    """
    current_settings = custom_logging_settings if custom_logging_settings is not None else global_app_settings.logging

    logger.remove()

    logger.add(
        sys.stderr,
        level=current_settings.LOG_LEVEL.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
        enqueue=True # Essential for async safety and performance
    )

    # Ensure log directories exist before adding file sinks
    if current_settings.LOG_FILE_PATH: # Ensure Path object
        current_settings.LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(current_settings.LOG_FILE_PATH), # Loguru expects string path
            rotation=current_settings.LOG_ROTATION_SIZE,
            retention=current_settings.LOG_RETENTION_POLICY,
            level=current_settings.LOG_LEVEL.upper(),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            enqueue=True, # For async safety
            # compression="zip" # Optional: for compressed logs
        )

    if current_settings.ERROR_LOG_FILE_PATH: # Ensure Path object
        current_settings.ERROR_LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(current_settings.ERROR_LOG_FILE_PATH), # Loguru expects string path
            rotation=current_settings.LOG_ROTATION_SIZE, # Can be configured differently if needed
            retention=current_settings.LOG_RETENTION_POLICY, # Can be configured differently
            level="ERROR", # Only log errors and above to this file
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            enqueue=True, # For async safety
            # compression="zip" # Optional
        )
    
    return logger

# Initialize the logger instance for the module
# This ensures setup_logger is called when utils.py is imported.
logger = setup_logger()

# --- Async Retry Decorator ---
def async_retry(
    max_retries_override: Optional[int] = None, # Renamed for clarity
    delay_seconds: float = 1.0, # Initial delay
    backoff_factor: float = 2.0, # Factor to multiply delay by after each retry
    jitter_factor: float = 0.5, # Percentage of delay to use as jitter range (+/-)
    exceptions: tuple = (Exception,), # Tuple of exception types to retry on
    retry_logger: Optional[logger] = None # Optional custom logger instance
):
    """
    Asynchronous retry decorator with exponential backoff and jitter.
    MAX_RETRIES is read at call time from global settings if not overridden.
    """
    
    _logger = retry_logger if retry_logger is not None else logger # Use provided logger or default

    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Determine effective_max_retries at call time
            current_max_retries = max_retries_override
            if current_max_retries is None: # If not overridden, try to get from global settings
                try:
                    # Accessing nested Pydantic models correctly
                    current_max_retries = global_app_settings.crawler.MAX_RETRIES
                except AttributeError: # Fallback if settings structure is unexpected or not fully loaded
                    _logger.warning("Could not read MAX_RETRIES from global_app_settings.crawler for retry, defaulting to 3.")
                    current_max_retries = 3
            
            current_delay = delay_seconds
            # Loop for initial attempt (0) + number of retries
            for attempt in range(current_max_retries + 1): # +1 for the initial attempt
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == current_max_retries: # Last attempt failed
                        _logger.error(
                            f"Function '{func.__name__}' failed after {current_max_retries + 1} attempts. Last error: {type(e).__name__}: {e}"
                        )
                        raise # Re-raise the last exception

                    # Calculate jitter for the current delay
                    jitter = random.uniform(-jitter_factor, jitter_factor) * current_delay
                    actual_sleep_time = max(0, current_delay + jitter) # Ensure sleep time is not negative

                    _logger.warning(
                        f"Attempt {attempt + 1}/{current_max_retries + 1} for '{func.__name__}' failed with {type(e).__name__}: {e}. "
                        f"Retrying in {actual_sleep_time:.2f}s (delay: {current_delay:.2f}s, jitter: {jitter:.2f}s)..."
                    )
                    
                    await asyncio.sleep(actual_sleep_time)
                    current_delay *= backoff_factor # Increase delay for next potential retry
            # This line should be unreachable if logic is correct and an exception is always raised on final failure.
            # However, to satisfy linters/type checkers that expect a return value:
            _logger.critical(f"Reached unexpected end of retry wrapper for {func.__name__}. This should not happen.")
            return None # Should be unreachable
        return wrapper
    return decorator

# --- Text Cleaning & Normalization ---
def clean_text(text: Optional[str]) -> Optional[str]:
    if text is None: return None
    text = text.strip()
    text = re.sub(r'\s+', ' ', text) # Collapses multiple whitespace characters into a single space
    return text if text else None # Return None if text becomes empty after stripping

EMAIL_REGEX_PATTERN = r"[a-zA-Z0-9!#$%&'*+/=?^_`{|}~.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" # More permissive local part based on common standards
COMPILED_EMAIL_REGEX = re.compile(EMAIL_REGEX_PATTERN)

def normalize_email(email: Optional[str]) -> Optional[str]:
    if email is None: return None
    email = email.lower().strip()
    # Basic structural validation with regex; more comprehensive validation by email_validator in scraper
    match = COMPILED_EMAIL_REGEX.fullmatch(email)
    return email if match else None

def extract_emails_from_text(text: Optional[str]) -> List[str]:
    if not text: return []
    # Find all potential email-like strings
    found_emails = COMPILED_EMAIL_REGEX.findall(text)
    # Normalize and deduplicate
    normalized_emails = sorted(list(set(normalize_email(email) for email in found_emails if normalize_email(email))))
    return normalized_emails

# --- URL Parsing & Manipulation ---
def extract_domain(url: Optional[str], include_subdomain: bool = False) -> Optional[str]:
    if not url: return None
    
    # Handle mailto and tel links early
    parsed_original_scheme = urlparse(url)
    if parsed_original_scheme.scheme.lower() in ('mailto', 'tel'):
        return None

    try:
        ext = tldextract.extract(url)
        if not ext.suffix: # No valid TLD found
            # Check if it's an IP address or localhost, which tldextract might not classify with a suffix
            parsed_url_for_ip = urlparse(url if "://" in url else "http://" + url)
            if parsed_url_for_ip.hostname:
                # Regex for IP address
                ip_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
                if re.match(ip_pattern, parsed_url_for_ip.hostname) or parsed_url_for_ip.hostname.lower() == "localhost":
                    return parsed_url_for_ip.hostname # Return the IP or "localhost"
            return None # Not a valid domain if no suffix and not IP/localhost

        if include_subdomain:
            if ext.subdomain:
                return f"{ext.subdomain}.{ext.domain}.{ext.suffix}"
            else: # No subdomain, just domain and suffix
                return f"{ext.domain}.{ext.suffix}"
        else: # Only domain and suffix
            return f"{ext.domain}.{ext.suffix}"
    except Exception as e:
        logger.trace(f"tldextract failed for URL '{url}': {e}")
        return None


def make_absolute_url(base_url: str, relative_or_absolute_url: Optional[str]) -> Optional[str]:
    if not relative_or_absolute_url:
        return None # Return None if the input URL is None
    
    processed_url = relative_or_absolute_url.strip()
    if not processed_url:
        # If the relative URL is empty or whitespace, behavior can be debated.
        # Returning base_url might be one option, or None if it implies an error.
        # For now, let's assume an empty relative_url means "current page", so base_url.
        # However, if base_url is a directory, this could be ambiguous.
        # Returning None is safer if an empty string is not a valid relative path.
        # Considering the context of scraping hrefs, an empty href is usually not useful.
        return None

    parsed_relative = urlparse(processed_url)

    if parsed_relative.scheme: # Already an absolute URL
        return processed_url

    # Handle schemeless URLs like "//example.com/path"
    # urljoin handles this correctly by default if base_url has a scheme.
    # if processed_url.startswith("//"):
    #     base_scheme = urlparse(base_url).scheme
    #     return f"{base_scheme}:{processed_url}"

    # Handle cases like href="www.example.com/page" (lacks scheme but implies http/https)
    # This is a common pattern in poorly written HTML.
    # A simple check: if it starts with "www." and has no scheme, prepend "http://"
    # More robust: check if path looks like a domain.
    # urlparse("www.example.com/foo").path is "www.example.com/foo" if no scheme.
    # urlparse("http://www.example.com/foo").netloc is "www.example.com"
    if not parsed_relative.scheme and (parsed_relative.path.count('.') > 0 or parsed_relative.netloc) \
       and (processed_url.startswith("www.") or (parsed_relative.path and '.' in parsed_relative.path.split('/')[0])):
        try:
            # Attempt to parse by adding a default scheme
            potential_abs_parsed = urlparse("http://" + processed_url)
            if potential_abs_parsed.netloc: # If adding a scheme gives a valid netloc
                return potential_abs_parsed.geturl()
        except Exception:
            pass # Fall through to urljoin

    try:
        return urljoin(base_url, processed_url)
    except ValueError:
        logger.warning(f"Could not join base_url '{base_url}' and relative_url '{processed_url}'")
        return None

# --- Domain Rate Limiter Class ---
class DomainRateLimiter:
    def __init__(self):
        self._domain_locks: dict[str, asyncio.Lock] = {} # Ensures atomic updates to _last_request_time
        self._last_request_time: dict[str, float] = {}   # Tracks last request time for delay calculation
        self._domain_semaphores: dict[str, asyncio.Semaphore] = {} # Limits concurrent requests per domain
        # This lock protects the dictionaries themselves during GOC operations.
        self._registry_lock: asyncio.Lock = asyncio.Lock()
        logger.info("DomainRateLimiter initialized.")

    async def _get_or_create_domain_specific_resources(self, domain: str):
        """Safely gets or creates locks and semaphores for a domain."""
        if domain not in self._domain_semaphores: # Quick check without lock
            async with self._registry_lock: # Lock before modifying shared dictionaries
                if domain not in self._domain_semaphores: # Double check after acquiring lock
                    self._domain_locks[domain] = asyncio.Lock()
                    try:
                        concurrency = global_app_settings.MAX_CONCURRENT_REQUESTS_PER_DOMAIN
                    except AttributeError:
                        logger.warning("MAX_CONCURRENT_REQUESTS_PER_DOMAIN not in settings, defaulting to 1 for DRL.")
                        concurrency = 1
                    self._domain_semaphores[domain] = asyncio.Semaphore(concurrency)
                    self._last_request_time[domain] = 0.0 # Initialize last request time

    async def acquire(self, domain: str) -> None:
        """Acquires a permit for the domain, respecting concurrency and delay."""
        await self._get_or_create_domain_specific_resources(domain)
        
        domain_semaphore = self._domain_semaphores[domain]
        await domain_semaphore.acquire() # Respect MAX_CONCURRENT_REQUESTS_PER_DOMAIN
        
        domain_access_lock = self._domain_locks[domain]
        async with domain_access_lock: # Ensure atomic read/update of _last_request_time and sleep
            current_time = time.monotonic()
            time_since_last = current_time - self._last_request_time.get(domain, 0.0)
            
            try:
                min_delay = global_app_settings.crawler.MIN_DELAY_PER_DOMAIN_SECONDS
                max_delay = global_app_settings.crawler.MAX_DELAY_PER_DOMAIN_SECONDS
            except AttributeError:
                logger.warning("MIN/MAX_DELAY_PER_DOMAIN_SECONDS not found, using defaults 1.0-5.0s for DRL.")
                min_delay = 1.0
                max_delay = 5.0
            
            # Ensure min_delay is not greater than max_delay
            if min_delay > max_delay: min_delay = max_delay

            required_delay = random.uniform(min_delay, max_delay)
            
            if time_since_last < required_delay:
                sleep_duration = required_delay - time_since_last
                logger.debug(
                    f"Rate limiting domain '{domain}': sleeping for {sleep_duration:.2f}s. "
                    f"(Required: {required_delay:.2f}s, Actual since last: {time_since_last:.2f}s)"
                )
                await asyncio.sleep(sleep_duration)
            
            self._last_request_time[domain] = time.monotonic() # Update last request time

    def release(self, domain: str) -> None:
        """Releases a permit for the domain."""
        if domain in self._domain_semaphores:
            self._domain_semaphores[domain].release()
            logger.trace(f"Released permit for domain '{domain}'.")
        else:
            # This might happen if acquire was never called for the domain (e.g. error before acquire)
            # or if the limiter was cleared/restarted.
            logger.warning(f"Attempted to release permit for unmanaged or unknown domain '{domain}'.")

    async def wait_for_domain(self, domain: str) -> "DomainRateLimiterContextManager":
        """Async context manager entry point."""
        await self.acquire(domain)
        return DomainRateLimiterContextManager(self, domain)

class DomainRateLimiterContextManager:
    def __init__(self, limiter: DomainRateLimiter, domain: str):
        self._limiter = limiter
        self._domain = domain

    async def __aenter__(self):
        # acquire has already been called by wait_for_domain
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._limiter.release(self._domain)

# Global instance of the rate limiter
domain_rate_limiter = DomainRateLimiter()

def example_utility_function(): # A simple function for testing logger setup
    logger.info("example_utility_function called from utils.py")
    return True