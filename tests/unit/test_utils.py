# tests/unit/test_utils.py
# Version: Gemini-2025-05-26 15:20 EDT
import pytest
import sys
from pathlib import Path
import time 
import os 
import asyncio 
from unittest.mock import AsyncMock, call 

PROJECT_ROOT_FOR_IMPORTS = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORTS))

from lead_gen_pipeline.utils import (
    setup_logger, 
    example_utility_function, 
    async_retry, 
    logger as utils_logger,
    clean_text,
    normalize_email,
    extract_emails_from_text,
    extract_domain,
    make_absolute_url,
    DomainRateLimiter, 
    domain_rate_limiter 
)
from lead_gen_pipeline.config import LoggingSettings, AppSettings, settings as global_app_settings, CrawlerSettings

@pytest.fixture(scope="function")
def test_logger_instance(tmp_path):
    temp_log_file = tmp_path / "test_app.log"
    temp_error_log_file = tmp_path / "test_error.log"
    test_logging_settings = LoggingSettings(
        LOG_LEVEL="DEBUG", 
        LOG_FILE_PATH=temp_log_file,
        ERROR_LOG_FILE_PATH=temp_error_log_file,
    )
    # Use the global logger instance from utils, but reconfigure it
    configured_logger = setup_logger(custom_logging_settings=test_logging_settings)
    yield configured_logger, temp_log_file, temp_error_log_file
    # Reset to default config after test by re-running setup_logger without custom settings
    # This assumes global_app_settings.logging holds the desired default.
    setup_logger(custom_logging_settings=global_app_settings.logging)


# --- Logging Tests ---
def test_logger_writes_to_app_log(test_logger_instance):
    logger, temp_log_file, _ = test_logger_instance
    unique_message = f"Test info message for app log @ {time.time()}"
    logger.info(unique_message)
    logger.complete() 
    with open(temp_log_file, "r") as f:
        log_content = f.read()
    assert unique_message in log_content
    assert "INFO" in log_content

def test_logger_writes_to_error_log(test_logger_instance):
    logger, _, temp_error_log_file = test_logger_instance
    unique_message = f"Test error message for error log @ {time.time()}"
    logger.error(unique_message)
    logger.complete()
    with open(temp_error_log_file, "r") as f:
        log_content = f.read()
    assert unique_message in log_content
    assert "ERROR" in log_content

def test_logger_debug_messages_logged_when_level_is_debug(tmp_path):
    temp_log_file = tmp_path / "debug_test_app.log"
    debug_logging_settings = LoggingSettings(
        LOG_LEVEL="DEBUG",
        LOG_FILE_PATH=temp_log_file,
        ERROR_LOG_FILE_PATH=tmp_path / "debug_test_error.log" 
    )
    logger = setup_logger(custom_logging_settings=debug_logging_settings)
    debug_message = f"This is a DEBUG message @ {time.time()}"
    logger.debug(debug_message)
    logger.complete()
    with open(temp_log_file, "r") as f:
        log_content = f.read()
    assert debug_message in log_content
    assert "DEBUG" in log_content
    setup_logger(custom_logging_settings=global_app_settings.logging) # Reset

def test_logger_debug_messages_not_logged_when_level_is_info(tmp_path):
    temp_log_file = tmp_path / "info_test_app.log"
    info_logging_settings = LoggingSettings(
        LOG_LEVEL="INFO",
        LOG_FILE_PATH=temp_log_file,
        ERROR_LOG_FILE_PATH=tmp_path / "info_test_error.log" 
    )
    logger = setup_logger(custom_logging_settings=info_logging_settings)
    debug_message = f"This is a DEBUG message (should not be logged) @ {time.time()}"
    info_message = f"This is an INFO message (should be logged) @ {time.time()}"
    logger.debug(debug_message)
    logger.info(info_message) 
    logger.complete()
    with open(temp_log_file, "r") as f:
        log_content = f.read()
    assert debug_message not in log_content
    assert info_message in log_content 
    setup_logger(custom_logging_settings=global_app_settings.logging) # Reset

def test_example_utility_function_logs_and_returns_true(test_logger_instance):
    logger, temp_log_file, _ = test_logger_instance 
    result = example_utility_function() 
    assert result is True
    logger.complete()
    with open(temp_log_file, "r") as f:
        log_content = f.read()
    assert "example_utility_function called from utils.py" in log_content

def test_setup_logger_with_global_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGGING__LOG_LEVEL", "WARNING")
    temp_global_log_path_str = str(tmp_path / "global_app_test.log")
    monkeypatch.setenv("LOGGING__LOG_FILE_PATH", temp_global_log_path_str)
    temp_global_error_log_path_str = str(tmp_path / "global_error_test.log")
    monkeypatch.setenv("LOGGING__ERROR_LOG_FILE_PATH", temp_global_error_log_path_str)

    # Reload AppSettings to pick up monkeypatched env vars
    current_app_settings = AppSettings(_env_file=None) 
    logger = setup_logger(custom_logging_settings=current_app_settings.logging)
    
    assert current_app_settings.logging.LOG_LEVEL == "WARNING"
    assert current_app_settings.logging.LOG_FILE_PATH.resolve() == Path(temp_global_log_path_str).resolve()
    assert current_app_settings.logging.ERROR_LOG_FILE_PATH.resolve() == Path(temp_global_error_log_path_str).resolve()

    info_message = f"Global INFO (should NOT be logged by WARNING level) @ {time.time()}"
    warning_message = f"Global WARNING (should be logged) @ {time.time()}"
    debug_message = f"Global DEBUG (should NOT be logged by WARNING level) @ {time.time()}"

    logger.info(info_message) 
    logger.warning(warning_message)
    logger.debug(debug_message)
    logger.complete()

    with open(current_app_settings.logging.LOG_FILE_PATH, "r") as f:
        log_content = f.read()
    
    assert info_message not in log_content
    assert warning_message in log_content
    assert debug_message not in log_content
    setup_logger(custom_logging_settings=global_app_settings.logging) # Reset

# --- Tests for async_retry decorator ---
class CustomRetryException(Exception): pass
class AnotherRetryException(Exception): pass

@pytest.mark.asyncio
async def test_async_retry_succeeds_on_first_try(test_logger_instance):
    logger, temp_log_file, _ = test_logger_instance
    @async_retry(max_retries_override=2, delay_seconds=0.01, retry_logger=logger) # CORRECTED
    async def func_succeeds(): return "success"
    result = await func_succeeds()
    assert result == "success"
    logger.complete()
    with open(temp_log_file, "r") as f: log_content = f.read()
    assert "Retrying in" not in log_content

@pytest.mark.asyncio
async def test_async_retry_succeeds_after_failures(test_logger_instance):
    logger, temp_log_file, _ = test_logger_instance
    mock_func = AsyncMock()
    mock_func.side_effect = [CustomRetryException("Attempt 1 fails"), CustomRetryException("Attempt 2 fails"), "success"]
    @async_retry(max_retries_override=2, delay_seconds=0.01, exceptions=(CustomRetryException,), retry_logger=logger) # CORRECTED
    async def func_to_retry(): return await mock_func()
    result = await func_to_retry()
    assert result == "success"
    assert mock_func.call_count == 3
    logger.complete()
    with open(temp_log_file, "r") as f: log_content = f.read()
    assert "Retrying in" in log_content
    assert "Attempt 1/3" in log_content 
    assert "Attempt 2/3" in log_content 

@pytest.mark.asyncio
async def test_async_retry_fails_after_max_retries(test_logger_instance):
    logger, temp_log_file, temp_error_log_file = test_logger_instance
    mock_func = AsyncMock(side_effect=CustomRetryException("Always fails"))
    @async_retry(max_retries_override=2, delay_seconds=0.01, exceptions=(CustomRetryException,), retry_logger=logger) # CORRECTED
    async def func_always_fails(): return await mock_func()
    with pytest.raises(CustomRetryException, match="Always fails"):
        await func_always_fails()
    assert mock_func.call_count == 3 
    logger.complete()
    with open(temp_log_file, "r") as f: log_content = f.read()
    assert "Retrying in" in log_content
    with open(temp_error_log_file, "r") as f: error_log_content = f.read()
    assert "failed after 3 attempts" in error_log_content

@pytest.mark.asyncio
async def test_async_retry_uses_default_max_retries_from_settings(monkeypatch, test_logger_instance):
    logger, temp_log_file, _ = test_logger_instance
    # Ensure we get the live settings for monkeypatching
    # This test relies on max_retries_override being None in the decorator call
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_RETRIES', 1) 
    
    mock_func = AsyncMock()
    mock_func.side_effect = [CustomRetryException("Fail 1"), "Success on 2nd call"]
    # Call without max_retries_override to test global setting usage
    @async_retry(delay_seconds=0.01, exceptions=(CustomRetryException,), retry_logger=logger) 
    async def func_uses_settings_retries(): return await mock_func()
    
    result = await func_uses_settings_retries()
    assert result == "Success on 2nd call"
    assert mock_func.call_count == 2 
    logger.complete()
    with open(temp_log_file, "r") as f: log_content = f.read()
    # Max retries is 1, so 1 initial attempt + 1 retry = 2 total attempts.
    # Log message for retry: "Attempt 1/2" (1st attempt failed, now on 1st retry out of 1 max retry)
    assert "Attempt 1/2" in log_content 

@pytest.mark.asyncio
async def test_async_retry_only_catches_specified_exceptions(test_logger_instance):
    logger, _, _ = test_logger_instance
    mock_func = AsyncMock(side_effect=ValueError("This is a ValueError"))
    @async_retry(max_retries_override=1, delay_seconds=0.01, exceptions=(CustomRetryException,), retry_logger=logger) # CORRECTED
    async def func_specific_exception(): return await mock_func()
    with pytest.raises(ValueError, match="This is a ValueError"):
        await func_specific_exception()
    assert mock_func.call_count == 1

# --- Text/URL Utilities Tests ---
@pytest.mark.parametrize("text_input, expected_output", [
    ("  hello world   ", "hello world"), ("hello    world", "hello world"),
    ("\t hello \n world \r", "hello world"), ("   ", None), ("", None), (None, None), ("single", "single")
])
def test_clean_text(text_input, expected_output):
    assert clean_text(text_input) == expected_output

@pytest.mark.parametrize("email_input, expected_output", [
    (" test@example.com ", "test@example.com"), ("TEST@EXAMPLE.COM", "test@example.com"),
    ("invalid-email", None), ("test@example", None), ("test@.com", None), (None, None),
    ("user.name+tag@example.com", "user.name+tag@example.com"), ("", None)
])
def test_normalize_email(email_input, expected_output):
    assert normalize_email(email_input) == expected_output

@pytest.mark.parametrize("text_input, expected_emails", [
    ("Contact us at info@example.com or sales@example.com.", ["info@example.com", "sales@example.com"]),
    ("No emails here.", []),
    ("My email is Test@Example.Co.Uk and another is USER@DOMAIN.INFO.", ["test@example.co.uk", "user@domain.info"]),
    ("Invalid: test@domain incomplete@ test@.com", []), (None, []),
    ("Email: foo@bar.com, then bar@foo.com.", ["bar@foo.com", "foo@bar.com"]) # Sorted
])
def test_extract_emails_from_text(text_input, expected_emails):
    assert extract_emails_from_text(text_input) == expected_emails

@pytest.mark.parametrize("url_input, include_subdomain, expected_domain", [
    ("http://www.example.com/path", False, "example.com"),
    ("https://sub.example.co.uk/path?query=1", False, "example.co.uk"),
    ("ftp://example.com", False, "example.com"),
    ("www.example.com", False, "example.com"), 
    ("example.com", False, "example.com"),     
    ("http://localhost:8000", False, "localhost"), 
    ("http://127.0.0.1/test", False, "127.0.0.1"), 
    (None, False, None), ("", False, None),
    ("http://www.example.com/path", True, "www.example.com"),
    ("https://sub.example.com", True, "sub.example.com"),
    ("https://another.sub.example.co.uk", True, "another.sub.example.co.uk"),
    ("https://another.sub.example.co.uk", False, "example.co.uk"),
    ("mailto:test@example.com", False, None), 
    ("tel:1234567890", False, None),         
    ("justaword", False, None), 
    ("word.word", False, None) 
])
def test_extract_domain(url_input, include_subdomain, expected_domain):
    assert extract_domain(url_input, include_subdomain) == expected_domain

@pytest.mark.parametrize("base_url, relative_url, expected_absolute_url", [
    ("http://www.example.com/path/", "page.html", "http://www.example.com/path/page.html"),
    ("http://www.example.com/path", "page.html", "http://www.example.com/page.html"),
    ("http://www.example.com", "/abs/page.html", "http://www.example.com/abs/page.html"),
    ("http://www.example.com", "http://othersite.com/page", "http://othersite.com/page"),
    ("http://www.example.com", None, None),
    ("http://www.example.com/path/", "   ", "http://www.example.com/path/"), 
    ("http://www.example.com/path", "   ", "http://www.example.com/path"), 
    ("http://www.example.com", "   ", "http://www.example.com"), 
    ("http://www.example.com", "  page.html  ", "http://www.example.com/page.html"),
])
def test_make_absolute_url(base_url, relative_url, expected_absolute_url):
    assert make_absolute_url(base_url, relative_url) == expected_absolute_url

# --- Tests for DomainRateLimiter ---
@pytest.mark.asyncio
async def test_domain_rate_limiter_delays_requests(monkeypatch, test_logger_instance):
    logger, temp_log_file, _ = test_logger_instance
    
    # Monkeypatch global settings that DomainRateLimiter will use
    monkeypatch.setattr(global_app_settings.crawler, 'MIN_DELAY_PER_DOMAIN_SECONDS', 0.1)
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_DELAY_PER_DOMAIN_SECONDS', 0.2)
    monkeypatch.setattr(global_app_settings, 'MAX_CONCURRENT_REQUESTS_PER_DOMAIN', 1)


    limiter = DomainRateLimiter() 
    domain = "testdomain-delay.com" 
    
    start_time = asyncio.get_event_loop().time()
    async with await limiter.wait_for_domain(domain): 
        logger.info(f"First access to {domain}")
    first_request_end_time = asyncio.get_event_loop().time()
    
    async with await limiter.wait_for_domain(domain): 
        logger.info(f"Second access to {domain}")
    second_request_end_time = asyncio.get_event_loop().time()

    duration_first_pass = first_request_end_time - start_time
    duration_second_pass_wait = second_request_end_time - first_request_end_time
    
    logger.info(f"Duration first pass for {domain}: {duration_first_pass}, Second pass wait: {duration_second_pass_wait}")
    logger.complete()
    
    min_delay_for_assert = global_app_settings.crawler.MIN_DELAY_PER_DOMAIN_SECONDS
    assert duration_second_pass_wait >= min_delay_for_assert * 0.8 
    
    with open(temp_log_file, "r") as f:
        log_content = f.read()
    assert f"Rate limiting domain '{domain}'" in log_content

@pytest.mark.asyncio
async def test_domain_rate_limiter_concurrency(monkeypatch, test_logger_instance):
    logger, temp_log_file, _ = test_logger_instance

    monkeypatch.setattr(global_app_settings.crawler, 'MIN_DELAY_PER_DOMAIN_SECONDS', 0.01)
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_DELAY_PER_DOMAIN_SECONDS', 0.02)
    monkeypatch.setattr(global_app_settings, 'MAX_CONCURRENT_REQUESTS_PER_DOMAIN', 1)

    limiter = DomainRateLimiter()
    domain = "concurrenttest-sem.com" 
    
    active_workers = 0
    max_active_workers = 0
    worker_lock = asyncio.Lock()

    async def worker(id_num): 
        nonlocal active_workers, max_active_workers
        async with await limiter.wait_for_domain(domain): 
            async with worker_lock:
                active_workers += 1
                max_active_workers = max(max_active_workers, active_workers)
            logger.info(f"Worker {id_num} acquired permit for {domain}, active: {active_workers}")
            await asyncio.sleep(0.1) 
            async with worker_lock:
                active_workers -= 1
            logger.info(f"Worker {id_num} releasing permit for {domain}, active: {active_workers}")

    tasks = [asyncio.create_task(worker(i)) for i in range(3)]
    await asyncio.gather(*tasks)
    
    assert max_active_workers == global_app_settings.MAX_CONCURRENT_REQUESTS_PER_DOMAIN
    logger.complete()

if __name__ == "__main__":
    pytest.main()

