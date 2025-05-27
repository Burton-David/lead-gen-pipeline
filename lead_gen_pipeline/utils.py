# lead_gen_pipeline/utils.py
# Version: 2025-05-22 20:45 UTC 
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
    from lead_gen_pipeline.config import LoggingSettings, AppSettings, settings as global_app_settings


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
        enqueue=True
    )

    if current_settings.LOG_FILE_PATH: 
        current_settings.LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(current_settings.LOG_FILE_PATH), 
            rotation=current_settings.LOG_ROTATION_SIZE,
            retention=current_settings.LOG_RETENTION_POLICY,
            level=current_settings.LOG_LEVEL.upper(),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            enqueue=True,
        )

    if current_settings.ERROR_LOG_FILE_PATH: 
        current_settings.ERROR_LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(current_settings.ERROR_LOG_FILE_PATH), 
            rotation=current_settings.LOG_ROTATION_SIZE,
            retention=current_settings.LOG_RETENTION_POLICY,
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            enqueue=True,
        )
    
    return logger

logger = setup_logger()

# --- Async Retry Decorator ---
def async_retry(
    max_retries_override: Optional[int] = None, # Renamed for clarity
    delay_seconds: float = 1.0,
    backoff_factor: float = 2.0,
    jitter_factor: float = 0.5,
    exceptions: tuple = (Exception,),
    retry_logger: Optional[logger] = None
):
    """
    Asynchronous retry decorator with exponential backoff and jitter.
    MAX_RETRIES is read at call time from global settings if not overridden.
    """
    
    _logger = retry_logger if retry_logger is not None else logger

    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Determine effective_max_retries at call time
            current_max_retries = max_retries_override
            if current_max_retries is None:
                try:
                    current_max_retries = global_app_settings.crawler.MAX_RETRIES
                except AttributeError: 
                    _logger.warning("Could not read MAX_RETRIES from settings for retry, defaulting to 3.")
                    current_max_retries = 3
            
            current_delay = delay_seconds
            # Loop for initial attempt (0) + number of retries
            for attempt in range(current_max_retries + 1): 
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
    text = re.sub(r'\s+', ' ', text)
    return text if text else None

EMAIL_REGEX_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
COMPILED_EMAIL_REGEX = re.compile(EMAIL_REGEX_PATTERN)

def normalize_email(email: Optional[str]) -> Optional[str]:
    if email is None: return None
    email = email.lower().strip()
    match = COMPILED_EMAIL_REGEX.fullmatch(email)
    return email if match else None

def extract_emails_from_text(text: Optional[str]) -> List[str]:
    if not text: return []
    found_emails = COMPILED_EMAIL_REGEX.findall(text)
    normalized_emails = sorted(list(set(normalize_email(email) for email in found_emails if normalize_email(email))))
    return normalized_emails

# --- URL Parsing & Manipulation ---
def extract_domain(url: Optional[str], include_subdomain: bool = False) -> Optional[str]:
    if not url: return None
    parsed_original_scheme = urlparse(url)
    if parsed_original_scheme.scheme.lower() in ('mailto', 'tel'): return None
    ext = tldextract.extract(url)
    if not ext.suffix: 
        parsed_url_for_ip = urlparse(url if "://" in url else "http://" + url)
        if parsed_url_for_ip.hostname:
            ip_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
            if re.match(ip_pattern, parsed_url_for_ip.hostname) or parsed_url_for_ip.hostname.lower() == "localhost":
                return parsed_url_for_ip.hostname 
        return None 
    if include_subdomain:
        if ext.subdomain:
            return f"{ext.subdomain}.{ext.domain}.{ext.suffix}"
        else:
            return f"{ext.domain}.{ext.suffix}"
    else: 
        return f"{ext.domain}.{ext.suffix}"

def make_absolute_url(base_url: str, relative_or_absolute_url: Optional[str]) -> Optional[str]:
    if not relative_or_absolute_url: return None
    processed_url = relative_or_absolute_url.strip()
    if not processed_url: return base_url 
    if urlparse(processed_url).scheme: return processed_url
    try:
        return urljoin(base_url, processed_url)
    except ValueError:
        logger.warning(f"Could not join base_url '{base_url}' and relative_url '{processed_url}'")
        return None

# --- Domain Rate Limiter Class ---
class DomainRateLimiter:
    def __init__(self):
        self._domain_locks: dict[str, asyncio.Lock] = {} 
        self._last_request_time: dict[str, float] = {}
        self._domain_semaphores: dict[str, asyncio.Semaphore] = {}
        logger.info("DomainRateLimiter initialized.")

    def _get_or_create_domain_specific_locks(self, domain: str):
        if domain not in self._domain_locks:
            self._domain_locks[domain] = asyncio.Lock()
            try:
                concurrency = global_app_settings.MAX_CONCURRENT_REQUESTS_PER_DOMAIN
            except AttributeError:
                logger.warning("MAX_CONCURRENT_REQUESTS_PER_DOMAIN not found in global_app_settings, defaulting to 1.")
                concurrency = 1
            self._domain_semaphores[domain] = asyncio.Semaphore(concurrency)
            self._last_request_time[domain] = 0.0 

    async def acquire(self, domain: str) -> None:
        self._get_or_create_domain_specific_locks(domain)
        domain_semaphore = self._domain_semaphores[domain]
        await domain_semaphore.acquire() 
        async with self._domain_locks[domain]: 
            current_time = time.monotonic()
            time_since_last = current_time - self._last_request_time.get(domain, 0.0)
            try:
                min_delay = global_app_settings.crawler.MIN_DELAY_PER_DOMAIN_SECONDS
                max_delay = global_app_settings.crawler.MAX_DELAY_PER_DOMAIN_SECONDS
            except AttributeError:
                logger.warning("Delay settings (MIN/MAX_DELAY_PER_DOMAIN_SECONDS) not found in global_app_settings.crawler, using defaults for DomainRateLimiter.")
                min_delay = 1.0 
                max_delay = 5.0 
            required_delay = random.uniform(min_delay, max_delay)
            if time_since_last < required_delay:
                sleep_duration = required_delay - time_since_last
                logger.debug(
                    f"Rate limiting domain '{domain}': sleeping for {sleep_duration:.2f}s. "
                    f"(Required: {required_delay:.2f}s, Actual since last: {time_since_last:.2f}s)"
                )
                await asyncio.sleep(sleep_duration)
            self._last_request_time[domain] = time.monotonic()

    def release(self, domain: str) -> None:
        if domain in self._domain_semaphores:
            self._domain_semaphores[domain].release()
            logger.trace(f"Released permit for domain '{domain}'.") 
        else:
            logger.warning(f"Attempted to release permit for unmanaged domain '{domain}'.")

    async def wait_for_domain(self, domain: str) -> "DomainRateLimiterContextManager":
        await self.acquire(domain)
        return DomainRateLimiterContextManager(self, domain)

class DomainRateLimiterContextManager:
    def __init__(self, limiter: DomainRateLimiter, domain: str):
        self._limiter = limiter
        self._domain = domain
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._limiter.release(self._domain)

domain_rate_limiter = DomainRateLimiter()

def example_utility_function():
    logger.info("example_utility_function called from utils.py")
    return True
