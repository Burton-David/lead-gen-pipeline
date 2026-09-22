"""Shared utilities: logging setup, async retry, text/URL helpers, rate limiting."""

import asyncio
import random
import re
import sys
import time
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import urljoin, urlparse

import tldextract
from loguru import logger

if TYPE_CHECKING:
    from loguru import Logger

try:
    from .config import LoggingSettings
    from .config import settings as global_app_settings
except ImportError:
    from lead_gen_pipeline.config import LoggingSettings  # type: ignore
    from lead_gen_pipeline.config import settings as global_app_settings  # type: ignore

_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)
_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{name}:{function}:{line} - {message}"
)


def setup_logger(custom_logging_settings: LoggingSettings | None = None) -> "Logger":
    """Configure the shared loguru logger and return it.

    Adds a colourised stderr sink plus rotating file sinks for all logs and for errors
    only. Reuses the global loguru instance, so callers importing ``logger`` get the
    configured logger.
    """
    s = custom_logging_settings or global_app_settings.logging
    logger.remove()
    logger.add(
        sys.stderr,
        level=s.LOG_LEVEL.upper(),
        format=_CONSOLE_FORMAT,
        colorize=True,
        enqueue=True,  # async-safe
    )

    s.LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(s.LOG_FILE_PATH),
        rotation=s.LOG_ROTATION_SIZE,
        retention=s.LOG_RETENTION_POLICY,
        level=s.LOG_LEVEL.upper(),
        format=_FILE_FORMAT,
        enqueue=True,
    )

    s.ERROR_LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(s.ERROR_LOG_FILE_PATH),
        rotation=s.LOG_ROTATION_SIZE,
        retention=s.LOG_RETENTION_POLICY,
        level="ERROR",
        format=_FILE_FORMAT,
        enqueue=True,
    )
    return logger


# Configure the shared logger on import. setup_logger mutates and returns the global
# loguru instance, so importing `logger` elsewhere yields the configured logger.
setup_logger()


def async_retry(
    max_retries_override: int | None = None,
    delay_seconds: float = 1.0,
    backoff_factor: float = 2.0,
    jitter_factor: float = 0.5,
    exceptions: tuple = (Exception,),
    retry_logger: Optional["Logger"] = None,
) -> Callable[..., Any]:
    """Retry an async function with exponential backoff and jitter.

    When ``max_retries_override`` is None the retry count is read at call time from
    ``settings.crawler.MAX_RETRIES``, so tests can patch it dynamically.
    """
    _logger = retry_logger if retry_logger is not None else logger

    def decorator(
        func: Callable[..., Coroutine[Any, Any, Any]],
    ) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            max_retries = max_retries_override
            if max_retries is None:
                try:
                    max_retries = global_app_settings.crawler.MAX_RETRIES
                except AttributeError:
                    _logger.warning("MAX_RETRIES unreadable from settings; using 3.")
                    max_retries = 3

            delay = delay_seconds
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        _logger.error(
                            f"'{func.__name__}' failed after {max_retries + 1} "
                            f"attempts. Last error: {type(e).__name__}: {e}"
                        )
                        raise

                    jitter = random.uniform(-jitter_factor, jitter_factor) * delay
                    sleep_for = max(0, delay + jitter)
                    _logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} for "
                        f"'{func.__name__}' failed with {type(e).__name__}: {e}. "
                        f"Retrying in {sleep_for:.2f}s..."
                    )
                    await asyncio.sleep(sleep_for)
                    delay *= backoff_factor
            return None  # Unreachable: the final attempt always raises.

        return wrapper

    return decorator


def clean_text(text: str | None) -> str | None:
    """Strip and collapse internal whitespace; return None if empty."""
    if text is None:
        return None
    text = re.sub(r"\s+", " ", text.strip())
    return text if text else None


EMAIL_REGEX_PATTERN = r"[a-zA-Z0-9!#$%&'*+/=?^_`{|}~.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
COMPILED_EMAIL_REGEX = re.compile(EMAIL_REGEX_PATTERN)


def normalize_email(email: str | None) -> str | None:
    """Lowercase, trim, and structurally validate an email; return None if invalid."""
    if email is None:
        return None
    email = email.lower().strip()
    return email if COMPILED_EMAIL_REGEX.fullmatch(email) else None


def extract_emails_from_text(text: str | None) -> list[str]:
    """Return a sorted, deduplicated list of valid emails found in ``text``."""
    if not text:
        return []
    found = COMPILED_EMAIL_REGEX.findall(text)
    return sorted({normalized for e in found if (normalized := normalize_email(e))})


def extract_domain(url: str | None, include_subdomain: bool = False) -> str | None:
    """Return the registrable domain of a URL (or the IP/localhost host).

    Returns None for mailto:/tel: links and strings without a valid TLD or host.
    """
    if not url:
        return None
    if urlparse(url).scheme.lower() in ("mailto", "tel"):
        return None

    try:
        ext = tldextract.extract(url)
        if not ext.suffix:
            # No registrable suffix; accept bare IP addresses and localhost.
            host = urlparse(url if "://" in url else "http://" + url).hostname
            if host:
                ip_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
                if re.match(ip_pattern, host) or host.lower() == "localhost":
                    return host
            return None

        if include_subdomain and ext.subdomain:
            return f"{ext.subdomain}.{ext.domain}.{ext.suffix}"
        return f"{ext.domain}.{ext.suffix}"
    except Exception as e:
        logger.trace(f"tldextract failed for URL '{url}': {e}")
        return None


def make_absolute_url(
    base_url: str, relative_or_absolute_url: str | None
) -> str | None:
    """Resolve a possibly-relative URL against ``base_url``.

    Handles already-absolute URLs, schemeless ``www.`` hosts, and ordinary relative
    paths. Returns None for empty input.
    """
    if not relative_or_absolute_url:
        return None
    processed_url = relative_or_absolute_url.strip()
    if not processed_url:
        return None

    if urlparse(processed_url).scheme:
        return processed_url

    # A bare "www.host/path" with no scheme: treat it as an absolute URL. Anything else
    # (relative paths, "/abs", "//proto-relative") is left to urljoin, which handles
    # them correctly against an absolute base.
    if processed_url.startswith("www."):
        candidate = urlparse("http://" + processed_url)
        if candidate.netloc:
            return candidate.geturl()

    try:
        return urljoin(base_url, processed_url)
    except ValueError:
        logger.warning(f"Could not join '{base_url}' and '{processed_url}'")
        return None


class DomainRateLimiter:
    """Per-domain concurrency limit and minimum delay between requests.

    Each domain gets a concurrency semaphore and a lock that serialises the delay
    bookkeeping, so requests to one host stay politely spaced.
    """

    def __init__(self) -> None:
        self._domain_locks: dict[str, asyncio.Lock] = {}
        self._last_request_time: dict[str, float] = {}
        self._domain_semaphores: dict[str, asyncio.Semaphore] = {}
        self._registry_lock: asyncio.Lock = asyncio.Lock()
        logger.info("DomainRateLimiter initialized.")

    async def _get_or_create_domain_specific_resources(self, domain: str) -> None:
        if domain in self._domain_semaphores:
            return
        async with self._registry_lock:
            if domain not in self._domain_semaphores:
                self._domain_locks[domain] = asyncio.Lock()
                try:
                    concurrency = global_app_settings.MAX_CONCURRENT_REQUESTS_PER_DOMAIN
                except AttributeError:
                    logger.warning("Concurrency setting missing; defaulting to 1.")
                    concurrency = 1
                self._domain_semaphores[domain] = asyncio.Semaphore(concurrency)
                self._last_request_time[domain] = 0.0

    async def acquire(self, domain: str) -> None:
        """Acquire a permit for ``domain``, sleeping to honour the minimum delay."""
        await self._get_or_create_domain_specific_resources(domain)
        await self._domain_semaphores[domain].acquire()

        async with self._domain_locks[domain]:
            time_since_last = time.monotonic() - self._last_request_time.get(
                domain, 0.0
            )
            try:
                min_delay = global_app_settings.crawler.MIN_DELAY_PER_DOMAIN_SECONDS
                max_delay = global_app_settings.crawler.MAX_DELAY_PER_DOMAIN_SECONDS
            except AttributeError:
                logger.warning("Delay settings missing; using 1.0-5.0s defaults.")
                min_delay, max_delay = 1.0, 5.0
            min_delay = min(min_delay, max_delay)

            required_delay = random.uniform(min_delay, max_delay)
            if time_since_last < required_delay:
                sleep_duration = required_delay - time_since_last
                logger.debug(
                    f"Rate limiting domain '{domain}': sleeping {sleep_duration:.2f}s"
                )
                await asyncio.sleep(sleep_duration)
            self._last_request_time[domain] = time.monotonic()

    def release(self, domain: str) -> None:
        """Release a previously acquired permit for ``domain``."""
        if domain in self._domain_semaphores:
            self._domain_semaphores[domain].release()
            logger.trace(f"Released permit for domain '{domain}'.")
        else:
            logger.warning(f"Release requested for unknown domain '{domain}'.")

    async def wait_for_domain(self, domain: str) -> "DomainRateLimiterContextManager":
        """Acquire a permit and return an async context manager that releases it."""
        await self.acquire(domain)
        return DomainRateLimiterContextManager(self, domain)


class DomainRateLimiterContextManager:
    """Releases a :class:`DomainRateLimiter` permit on exit."""

    def __init__(self, limiter: DomainRateLimiter, domain: str) -> None:
        self._limiter = limiter
        self._domain = domain

    async def __aenter__(self) -> "DomainRateLimiterContextManager":
        return self

    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        self._limiter.release(self._domain)


# Shared rate limiter instance, used by all crawler instances.
domain_rate_limiter = DomainRateLimiter()
