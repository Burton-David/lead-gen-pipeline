"""Tests for shared utilities: logging, retry, text/URL helpers, rate limiting."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from lead_gen_pipeline.config import LoggingSettings
from lead_gen_pipeline.config import settings as global_app_settings
from lead_gen_pipeline.utils import (
    DomainRateLimiter,
    async_retry,
    clean_text,
    extract_domain,
    extract_emails_from_text,
    make_absolute_url,
    normalize_email,
    setup_logger,
)


@pytest.fixture
def file_logger(tmp_path):
    app_log = tmp_path / "app.log"
    err_log = tmp_path / "error.log"
    logger = setup_logger(
        LoggingSettings(
            LOG_LEVEL="DEBUG", LOG_FILE_PATH=app_log, ERROR_LOG_FILE_PATH=err_log
        )
    )
    yield logger, app_log, err_log
    setup_logger(global_app_settings.logging)


def test_logger_writes_info_and_error(file_logger):
    logger, app_log, err_log = file_logger
    logger.info("hello-info")
    logger.error("boom-error")
    logger.complete()
    assert "hello-info" in app_log.read_text()
    assert "boom-error" in err_log.read_text()
    # The error sink only captures ERROR and above.
    assert "hello-info" not in err_log.read_text()


def test_logger_respects_level(tmp_path):
    app_log = tmp_path / "info.log"
    logger = setup_logger(
        LoggingSettings(
            LOG_LEVEL="INFO",
            LOG_FILE_PATH=app_log,
            ERROR_LOG_FILE_PATH=tmp_path / "e.log",
        )
    )
    logger.debug("should-not-appear")
    logger.info("should-appear")
    logger.complete()
    content = app_log.read_text()
    assert "should-appear" in content
    assert "should-not-appear" not in content
    setup_logger(global_app_settings.logging)


class _RetryError(Exception):
    pass


@pytest.mark.asyncio
async def test_async_retry_succeeds_after_failures(file_logger):
    logger, app_log, _ = file_logger
    calls = AsyncMock(side_effect=[_RetryError("1"), _RetryError("2"), "ok"])

    @async_retry(
        max_retries_override=2,
        delay_seconds=0.001,
        exceptions=(_RetryError,),
        retry_logger=logger,
    )
    async def flaky():
        return await calls()

    assert await flaky() == "ok"
    assert calls.call_count == 3
    logger.complete()
    assert "Attempt 1/3" in app_log.read_text()


@pytest.mark.asyncio
async def test_async_retry_raises_after_exhaustion(file_logger):
    logger, _, err_log = file_logger
    calls = AsyncMock(side_effect=_RetryError("always"))

    @async_retry(
        max_retries_override=2,
        delay_seconds=0.001,
        exceptions=(_RetryError,),
        retry_logger=logger,
    )
    async def always_fails():
        return await calls()

    with pytest.raises(_RetryError, match="always"):
        await always_fails()
    assert calls.call_count == 3
    logger.complete()
    assert "failed after 3 attempts" in err_log.read_text()


@pytest.mark.asyncio
async def test_async_retry_ignores_unlisted_exceptions(file_logger):
    logger, _, _ = file_logger
    calls = AsyncMock(side_effect=ValueError("nope"))

    @async_retry(
        max_retries_override=2,
        delay_seconds=0.001,
        exceptions=(_RetryError,),
        retry_logger=logger,
    )
    async def func():
        return await calls()

    with pytest.raises(ValueError):
        await func()
    assert calls.call_count == 1


@pytest.mark.parametrize(
    "text_input, expected",
    [
        ("  hello world   ", "hello world"),
        ("hello    world", "hello world"),
        ("\t hello \n world \r", "hello world"),
        ("   ", None),
        ("", None),
        (None, None),
    ],
)
def test_clean_text(text_input, expected):
    assert clean_text(text_input) == expected


@pytest.mark.parametrize(
    "email_input, expected",
    [
        (" test@example.com ", "test@example.com"),
        ("TEST@EXAMPLE.COM", "test@example.com"),
        ("invalid-email", None),
        ("test@example", None),
        ("user.name+tag@example.com", "user.name+tag@example.com"),
        (None, None),
    ],
)
def test_normalize_email(email_input, expected):
    assert normalize_email(email_input) == expected


@pytest.mark.parametrize(
    "text_input, expected",
    [
        ("Contact info@a.com or sales@b.com.", ["info@a.com", "sales@b.com"]),
        ("No emails here.", []),
        ("Foo@Bar.com and FOO@bar.com", ["foo@bar.com"]),
        (None, []),
    ],
)
def test_extract_emails_from_text(text_input, expected):
    assert extract_emails_from_text(text_input) == expected


@pytest.mark.parametrize(
    "url, include_sub, expected",
    [
        ("http://www.example.com/path", False, "example.com"),
        ("https://sub.example.co.uk/p", False, "example.co.uk"),
        ("www.example.com", False, "example.com"),
        ("http://127.0.0.1/test", False, "127.0.0.1"),
        ("http://localhost:8000", False, "localhost"),
        ("https://sub.example.com", True, "sub.example.com"),
        ("mailto:test@example.com", False, None),
        ("tel:1234567890", False, None),
        (None, False, None),
        ("justaword", False, None),
    ],
)
def test_extract_domain(url, include_sub, expected):
    assert extract_domain(url, include_sub) == expected


@pytest.mark.parametrize(
    "base, rel, expected",
    [
        ("http://e.com/p/", "page.html", "http://e.com/p/page.html"),
        ("http://e.com", "/abs/p.html", "http://e.com/abs/p.html"),
        ("http://e.com", "http://other.com/p", "http://other.com/p"),
        ("http://e.com", None, None),
        ("http://e.com", "   ", None),
        ("http://e.com", "www.other.com/x", "http://www.other.com/x"),
    ],
)
def test_make_absolute_url(base, rel, expected):
    assert make_absolute_url(base, rel) == expected


@pytest.mark.asyncio
async def test_rate_limiter_enforces_delay(monkeypatch):
    monkeypatch.setattr(
        global_app_settings.crawler, "MIN_DELAY_PER_DOMAIN_SECONDS", 0.1
    )
    monkeypatch.setattr(
        global_app_settings.crawler, "MAX_DELAY_PER_DOMAIN_SECONDS", 0.15
    )
    monkeypatch.setattr(global_app_settings, "MAX_CONCURRENT_REQUESTS_PER_DOMAIN", 1)

    limiter = DomainRateLimiter()
    domain = "delay-test.com"
    loop = asyncio.get_running_loop()

    async with await limiter.wait_for_domain(domain):
        pass
    first = loop.time()
    async with await limiter.wait_for_domain(domain):
        pass
    second_wait = loop.time() - first

    assert second_wait >= 0.1 * 0.8


@pytest.mark.asyncio
async def test_rate_limiter_concurrency_cap(monkeypatch):
    monkeypatch.setattr(
        global_app_settings.crawler, "MIN_DELAY_PER_DOMAIN_SECONDS", 0.01
    )
    monkeypatch.setattr(
        global_app_settings.crawler, "MAX_DELAY_PER_DOMAIN_SECONDS", 0.02
    )
    monkeypatch.setattr(global_app_settings, "MAX_CONCURRENT_REQUESTS_PER_DOMAIN", 1)

    limiter = DomainRateLimiter()
    domain = "concurrency-test.com"
    active = 0
    peak = 0
    lock = asyncio.Lock()

    async def worker():
        nonlocal active, peak
        async with await limiter.wait_for_domain(domain):
            async with lock:
                active += 1
                peak = max(peak, active)
            await asyncio.sleep(0.05)
            async with lock:
                active -= 1

    await asyncio.gather(*(worker() for _ in range(3)))
    assert peak == 1
