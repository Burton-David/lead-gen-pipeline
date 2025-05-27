# tests/unit/test_crawler.py
# Version: 2025-05-23 17:00 EDT
import pytest
import httpx
import respx # Import respx directly
import asyncio
from pathlib import Path
import sys
import urllib.robotparser
import re # Import re for escaping
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock, call
from collections import OrderedDict

PROJECT_ROOT_FOR_IMPORTS = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORTS))

from lead_gen_pipeline.crawler import AsyncWebCrawler, RobotsTxtDisallowedError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightBaseError
from lead_gen_pipeline.config import settings as global_app_settings, AppSettings, CrawlerSettings, LoggingSettings
from lead_gen_pipeline.utils import logger as utils_logger, setup_logger

# --- Fixtures ---
@pytest.fixture
def crawler_instance(event_loop) -> AsyncWebCrawler:
    instance = AsyncWebCrawler()
    AsyncWebCrawler._playwright_instance = None
    AsyncWebCrawler._browser = None
    return instance

@pytest.fixture(scope="function")
def test_logger_instance_for_crawler(tmp_path):
    original_logging_settings = global_app_settings.logging
    temp_log_file = tmp_path / "crawler_test_app.log"
    temp_error_log_file = tmp_path / "crawler_test_error.log"
    test_logging_settings = LoggingSettings(
        LOG_LEVEL="DEBUG",
        LOG_FILE_PATH=temp_log_file,
        ERROR_LOG_FILE_PATH=temp_error_log_file,
    )
    configured_logger = setup_logger(custom_logging_settings=test_logging_settings)
    yield configured_logger, temp_log_file, temp_error_log_file
    setup_logger(custom_logging_settings=original_logging_settings)


@pytest.fixture
def mock_playwright_page_context():
    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_response = AsyncMock()

    mock_page.goto = AsyncMock(return_value=mock_response)
    mock_page.content = AsyncMock(return_value="<html><body>Playwright Content</body></html>")
    type(mock_page).url = PropertyMock(return_value="http://playwright.final.url/MOCK")

    type(mock_response).status = PropertyMock(return_value=200)
    mock_response.ok = PropertyMock(return_value=True)
    
    mock_context.close = AsyncMock()
    mock_page.close = AsyncMock()

    return mock_page, mock_context, mock_response

# --- Robots.txt Test Data ---
ROBOTS_TXT_ALLOW_ALL = """
User-agent: *
Disallow:
"""

ROBOTS_TXT_DISALLOW_PATH = """
User-agent: *
Disallow: /private/
Disallow: /confidential.html

User-agent: MySpecificBot
Disallow: /mybot-only-private/
"""

ROBOTS_TXT_EMPTY = ""


# --- Tests for HTTPX Fetching (Largely Unchanged) ---
@respx.mock # Decorator is used, no need to inject respx_router
@pytest.mark.asyncio
async def test_fetch_page_httpx_success(crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    url = "http://testsuccess.com"
    expected_html = "<html><body>Success!</body></html>"
    expected_status = 200
    # Use the imported respx object directly
    route = respx.get(url).mock(return_value=httpx.Response(expected_status, html=expected_html))
    html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=False)
    assert status == expected_status
    assert html == expected_html
    assert final_url == url
    assert route.call_count == 1

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_httpx_redirect(crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    initial_url = "http://redirectme.com"
    final_url_target = "http://finaldestination.com"
    expected_html = "<html><body>Redirected Content</body></html>"
    route1 = respx.get(initial_url).mock(return_value=httpx.Response(301, headers={"Location": final_url_target}))
    route2 = respx.get(final_url_target).mock(return_value=httpx.Response(200, html=expected_html))
    html, status, final_url_returned = await crawler_instance.fetch_page(initial_url, use_playwright=False)
    assert status == 200
    assert html == expected_html
    assert final_url_returned == final_url_target

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_httpx_404_error_no_retry(crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_RETRIES', 0)
    url = "http://notfound.com"
    respx.get(url).mock(return_value=httpx.Response(404))
    html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=False)
    assert status == 404
    assert html is None

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_httpx_500_error_no_retry(crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_RETRIES', 0)
    url = "http://servererror.com"
    respx.get(url).mock(return_value=httpx.Response(500))
    html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=False)
    assert status == 500
    assert html is None

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_httpx_timeout_no_retry(crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_RETRIES', 0)
    monkeypatch.setattr(crawler_instance.settings, 'DEFAULT_TIMEOUT_SECONDS', 0.1)
    url = "http://timeoutsite.com"
    request = httpx.Request("GET", url)
    respx.get(url).mock(side_effect=httpx.TimeoutException("Test timeout", request=request))
    html, status, final_url_returned = await crawler_instance.fetch_page(url, use_playwright=False)
    assert status == 408
    assert html is None

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_httpx_network_error_no_retry(crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_RETRIES', 0)
    url = "http://networkerror.com"
    request = httpx.Request("GET", url)
    respx.get(url).mock(side_effect=httpx.ConnectError("Test connection error", request=request))
    html, status, final_url_returned = await crawler_instance.fetch_page(url, use_playwright=False)
    assert status == 599
    assert html is None

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_uses_retry_decorator_successfully_httpx(crawler_instance: AsyncWebCrawler, monkeypatch, test_logger_instance_for_crawler):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    logger, temp_log_file, _ = test_logger_instance_for_crawler
    url = "http://retrytest-httpx.com"
    expected_html = "<html><body>Retry Success!</body></html>"
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_RETRIES', 1)
    mock_responses = [ httpx.Response(500), httpx.Response(200, html=expected_html) ]
    respx.get(url).mock(side_effect=mock_responses)
    with patch('lead_gen_pipeline.utils.asyncio.sleep', AsyncMock()):
        html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=False)
    assert status == 200
    assert html == expected_html

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_exhausts_retries_httpx(crawler_instance: AsyncWebCrawler, monkeypatch, test_logger_instance_for_crawler):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    logger, temp_log_file, temp_error_log_file = test_logger_instance_for_crawler
    url = "http://alwaysfail-httpx.com"
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_RETRIES', 1)
    respx.get(url).mock(return_value=httpx.Response(500))
    with patch('lead_gen_pipeline.utils.asyncio.sleep', AsyncMock()):
        html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=False)
    assert status == 500
    assert html is None


# --- Tests for Playwright Fetching (`_fetch_with_playwright`) ---
@pytest.mark.asyncio
@patch.object(AsyncWebCrawler, '_get_playwright_page', new_callable=AsyncMock)
async def test_fetch_with_playwright_success(mock_get_page, crawler_instance: AsyncWebCrawler, mock_playwright_page_context):
    mock_page, mock_context, mock_response = mock_playwright_page_context
    mock_get_page.return_value = (mock_page, mock_context)
    
    url = "http://playwrightsuccess.com"
    timeout_ms = 30000
    expected_html = "<html><body>Playwright Content</body></html>"
    expected_status = 200
    expected_final_url = "http://playwright.final.url/MOCK"

    type(mock_page).url = PropertyMock(return_value=expected_final_url)
    mock_page.content = AsyncMock(return_value=expected_html)
    type(mock_response).status = PropertyMock(return_value=expected_status)
    mock_page.goto.return_value = mock_response

    html, status, final_url = await crawler_instance._fetch_with_playwright(url, timeout_ms)

    assert html == expected_html
    assert status == expected_status
    assert final_url == expected_final_url

@pytest.mark.asyncio
@patch.object(AsyncWebCrawler, '_get_playwright_page', new_callable=AsyncMock)
async def test_fetch_with_playwright_timeout_error(mock_get_page, crawler_instance: AsyncWebCrawler, mock_playwright_page_context):
    mock_page, mock_context, _ = mock_playwright_page_context
    mock_get_page.return_value = (mock_page, mock_context)
    url = "http://playwrighttimeout.com"
    timeout_ms = 100 
    mock_page.goto.side_effect = PlaywrightTimeoutError("Test Playwright Timeout")
    with pytest.raises(PlaywrightTimeoutError, match="Test Playwright Timeout"):
        await crawler_instance._fetch_with_playwright(url, timeout_ms)
    mock_context.close.assert_awaited_once()

@pytest.mark.asyncio
@patch.object(AsyncWebCrawler, '_get_playwright_page', new_callable=AsyncMock)
async def test_fetch_with_playwright_base_error(mock_get_page, crawler_instance: AsyncWebCrawler, mock_playwright_page_context):
    mock_page, mock_context, _ = mock_playwright_page_context
    mock_get_page.return_value = (mock_page, mock_context)
    url = "http://playwrightbaseerror.com"
    timeout_ms = 30000
    mock_page.goto.side_effect = PlaywrightBaseError("Test Playwright Base Error")
    with pytest.raises(PlaywrightBaseError, match="Test Playwright Base Error"):
        await crawler_instance._fetch_with_playwright(url, timeout_ms)
    mock_context.close.assert_awaited_once()

@pytest.mark.asyncio
@patch.object(AsyncWebCrawler, '_get_playwright_page', new_callable=AsyncMock)
async def test_fetch_with_playwright_no_response_object(mock_get_page, crawler_instance: AsyncWebCrawler, mock_playwright_page_context):
    mock_page, mock_context, _ = mock_playwright_page_context
    mock_get_page.return_value = (mock_page, mock_context)
    mock_page.goto.return_value = None 
    url = "http://playwrightnoresponse.com"
    timeout_ms = 30000
    with pytest.raises(PlaywrightBaseError, match=f"Playwright navigation to {url} failed to return a response object."):
        await crawler_instance._fetch_with_playwright(url, timeout_ms)
    mock_context.close.assert_awaited_once()

# --- Tests for `fetch_page` using Playwright ---
@pytest.mark.asyncio
@patch('lead_gen_pipeline.crawler.AsyncWebCrawler._fetch_with_playwright', new_callable=AsyncMock)
async def test_fetch_page_uses_playwright_successfully(mock_internal_fetch_pw, crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    url = "http://useplaywright.com"
    expected_html = "<html>Playwright success</html>"
    expected_status = 200
    expected_final_url = "http://useplaywright.final.com"
    mock_internal_fetch_pw.return_value = (expected_html, expected_status, expected_final_url)
    monkeypatch.setattr(global_app_settings.crawler, 'USE_PLAYWRIGHT_BY_DEFAULT', True)

    with patch('lead_gen_pipeline.utils.domain_rate_limiter.wait_for_domain', AsyncMock()) as mock_rate_limiter:
        class DummyAsyncContextManager:
            async def __aenter__(self): return self
            async def __aexit__(self, exc_type, exc_val, exc_tb): pass
        mock_rate_limiter.return_value = DummyAsyncContextManager()
        html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=True)
    assert html == expected_html
    assert status == expected_status

@pytest.mark.asyncio
@patch('lead_gen_pipeline.crawler.AsyncWebCrawler._fetch_with_playwright', new_callable=AsyncMock)
async def test_fetch_page_playwright_retry_and_fail(mock_internal_fetch_pw, crawler_instance: AsyncWebCrawler, monkeypatch, test_logger_instance_for_crawler):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    logger, temp_log_file, temp_error_log_file = test_logger_instance_for_crawler
    url = "http://playwrightretryfail.com"
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_RETRIES', 1)
    mock_internal_fetch_pw.side_effect = PlaywrightTimeoutError("PW Timeout for retry test")

    with patch('lead_gen_pipeline.utils.asyncio.sleep', AsyncMock()):
        with patch('lead_gen_pipeline.utils.domain_rate_limiter.wait_for_domain', AsyncMock()) as mock_rate_limiter:
            class DummyAsyncContextManager:
                async def __aenter__(self): return self
                async def __aexit__(self, exc_type, exc_val, exc_tb): pass
            mock_rate_limiter.return_value = DummyAsyncContextManager()
            html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=True)
    assert html is None
    assert status == 598


# --- New Tests for Robots.txt Functionality ---

@respx.mock
@pytest.mark.asyncio
async def test_fetch_and_parse_robots_txt_success_https(crawler_instance: AsyncWebCrawler): 
    domain = "example.com"
    robots_url = f"https://{domain}/robots.txt"
    respx.get(robots_url).mock(return_value=httpx.Response(200, text=ROBOTS_TXT_ALLOW_ALL))
    
    parser = await crawler_instance._fetch_and_parse_robots_txt(domain)
    assert parser is not None
    assert isinstance(parser, urllib.robotparser.RobotFileParser)
    assert parser.can_fetch("*", f"https://{domain}/anypage.html") is True

@respx.mock
@pytest.mark.asyncio
async def test_fetch_and_parse_robots_txt_success_http_fallback(crawler_instance: AsyncWebCrawler): 
    domain = "fallback.com"
    robots_url_https = f"https://{domain}/robots.txt"
    robots_url_http = f"http://{domain}/robots.txt"
    respx.get(robots_url_https).mock(return_value=httpx.Response(500)) 
    respx.get(robots_url_http).mock(return_value=httpx.Response(200, text=ROBOTS_TXT_DISALLOW_PATH))
    
    parser = await crawler_instance._fetch_and_parse_robots_txt(domain)
    assert parser is not None
    assert parser.can_fetch("*", f"http://{domain}/allowed.html") is True
    assert parser.can_fetch("*", f"http://{domain}/private/page.html") is False

@respx.mock
@pytest.mark.asyncio
async def test_fetch_robots_txt_not_found_404(crawler_instance: AsyncWebCrawler): 
    domain = "notfoundrobots.com"
    robots_url_https = f"https://{domain}/robots.txt"
    robots_url_http = f"http://{domain}/robots.txt" 
    respx.get(robots_url_https).mock(return_value=httpx.Response(404))
    http_route = respx.get(robots_url_http) 
    
    parser = await crawler_instance._fetch_and_parse_robots_txt(domain)
    assert parser is None 
    assert http_route.call_count == 0


@respx.mock
@pytest.mark.asyncio
async def test_fetch_robots_txt_network_error(crawler_instance: AsyncWebCrawler): 
    domain = "networkerrorrobots.com"
    robots_url = f"https://{domain}/robots.txt"
    request = httpx.Request("GET", robots_url) 
    respx.get(robots_url).mock(side_effect=httpx.ConnectError("Connection failed", request=request))
    
    parser = await crawler_instance._fetch_and_parse_robots_txt(domain)
    assert parser is None

@pytest.mark.asyncio
async def test_get_robots_parser_caching(crawler_instance: AsyncWebCrawler, monkeypatch):
    domain = "cachetest.com"
    mock_parser_instance = urllib.robotparser.RobotFileParser()
    mock_parser_instance.parse(ROBOTS_TXT_ALLOW_ALL.splitlines())

    mock_fetch_parse = AsyncMock(return_value=mock_parser_instance)
    monkeypatch.setattr(crawler_instance, '_fetch_and_parse_robots_txt', mock_fetch_parse)

    parser1 = await crawler_instance._get_robots_parser(domain)
    assert parser1 == mock_parser_instance
    mock_fetch_parse.assert_awaited_once_with(domain)
    assert domain in crawler_instance._robots_parsers_cache

    parser2 = await crawler_instance._get_robots_parser(domain)
    assert parser2 == mock_parser_instance
    mock_fetch_parse.assert_awaited_once() 

    monkeypatch.setattr(crawler_instance.settings, 'ROBOTS_TXT_CACHE_SIZE', 1)
    await crawler_instance._get_robots_parser("anotherdomain.com") 
    assert domain not in crawler_instance._robots_parsers_cache 
    assert "anotherdomain.com" in crawler_instance._robots_parsers_cache
    assert mock_fetch_parse.call_count == 2


@pytest.mark.asyncio
async def test_check_robots_txt_allowed(crawler_instance: AsyncWebCrawler, monkeypatch):
    url = "http://alloweddomain.com/allowed/path"
    domain = "alloweddomain.com"
    mock_parser = MagicMock(spec=urllib.robotparser.RobotFileParser)
    mock_parser.can_fetch.return_value = True
    
    monkeypatch.setattr(crawler_instance, '_get_robots_parser', AsyncMock(return_value=mock_parser))
    
    await crawler_instance._check_robots_txt(url) 
    crawler_instance._get_robots_parser.assert_awaited_once_with(domain)
    mock_parser.can_fetch.assert_called_once_with(crawler_instance.settings.ROBOTS_TXT_USER_AGENT, url)

@pytest.mark.asyncio
async def test_check_robots_txt_disallowed(crawler_instance: AsyncWebCrawler, monkeypatch):
    url = "http://disalloweddomain.com/forbidden/path"
    domain = "disalloweddomain.com"
    user_agent = crawler_instance.settings.ROBOTS_TXT_USER_AGENT # Should be '*' by default
    
    mock_parser = MagicMock(spec=urllib.robotparser.RobotFileParser)
    mock_parser.can_fetch.return_value = False # Simulate disallowed
    
    monkeypatch.setattr(crawler_instance, '_get_robots_parser', AsyncMock(return_value=mock_parser))
    
    expected_message = f"URL '{url}' is disallowed for user-agent '{user_agent}' by robots.txt."
    with pytest.raises(RobotsTxtDisallowedError, match=re.escape(expected_message)):
        await crawler_instance._check_robots_txt(url)
    crawler_instance._get_robots_parser.assert_awaited_once_with(domain)
    mock_parser.can_fetch.assert_called_once_with(user_agent, url)

@pytest.mark.asyncio
async def test_check_robots_txt_no_parser_is_permissive(crawler_instance: AsyncWebCrawler, monkeypatch):
    url = "http://noparserdomain.com/some/path"
    monkeypatch.setattr(crawler_instance, '_get_robots_parser', AsyncMock(return_value=None))
    await crawler_instance._check_robots_txt(url)

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_respects_robots_txt_disallowed(crawler_instance: AsyncWebCrawler, monkeypatch): 
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', True)
    monkeypatch.setattr(crawler_instance.settings, 'ROBOTS_TXT_USER_AGENT', 'TestAgent')
    
    domain = "robotstest.com"
    url_allowed = f"http://{domain}/allowed.html"
    url_disallowed = f"http://{domain}/disallowed.html"
    
    robots_content = "User-agent: TestAgent\nDisallow: /disallowed.html"
    respx.get(f"https://{domain}/robots.txt").mock(return_value=httpx.Response(200, text=robots_content))
    respx.get(f"http://{domain}/robots.txt").mock(return_value=httpx.Response(404))

    respx.get(url_allowed).mock(return_value=httpx.Response(200, html="Allowed page"))
    disallowed_route = respx.get(url_disallowed) 

    html, status, _ = await crawler_instance.fetch_page(url_allowed, use_playwright=False)
    assert status == 200
    assert html == "Allowed page"

    html, status, final_url = await crawler_instance.fetch_page(url_disallowed, use_playwright=False)
    assert html is None
    assert status == 403 
    assert final_url == url_disallowed
    assert disallowed_route.call_count == 0

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_respect_robots_txt_off(crawler_instance: AsyncWebCrawler, monkeypatch): 
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False) 
    
    domain = "robotsoff.com"
    url_disallowed_by_rules = f"http://{domain}/disallowed.html"
        
    page_route = respx.get(url_disallowed_by_rules).mock(return_value=httpx.Response(200, html="Fetched anyway"))

    # Patch _check_robots_txt to ensure it's not called when RESPECT_ROBOTS_TXT is False
    with patch.object(crawler_instance, '_check_robots_txt', new_callable=AsyncMock) as mock_check_robots:
        html, status, _ = await crawler_instance.fetch_page(url_disallowed_by_rules, use_playwright=False)
    
    assert status == 200
    assert html == "Fetched anyway"
    mock_check_robots.assert_not_awaited() 
    assert page_route.call_count == 1


@pytest.mark.asyncio
async def test_crawler_close_clears_robots_cache(crawler_instance: AsyncWebCrawler, monkeypatch):
    domain = "domain1.com"
    mock_parser = urllib.robotparser.RobotFileParser()
    crawler_instance._robots_parsers_cache[domain] = mock_parser
    crawler_instance._robots_fetch_locks[domain] = asyncio.Lock()
    assert domain in crawler_instance._robots_parsers_cache
    assert domain in crawler_instance._robots_fetch_locks

    monkeypatch.setattr(AsyncWebCrawler, 'close_playwright_resources', AsyncMock())

    await crawler_instance.close()
    
    assert not crawler_instance._robots_parsers_cache 
    assert not crawler_instance._robots_fetch_locks 
    AsyncWebCrawler.close_playwright_resources.assert_awaited_once()


# --- General Crawler Tests ---
@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_rate_limiter_called_httpx(crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    url = "http://ratelimited-httpx.com"
    respx.get(url).mock(return_value=httpx.Response(200, html="OK"))
    with patch('lead_gen_pipeline.utils.domain_rate_limiter.wait_for_domain', AsyncMock()) as mock_wait_for_domain:
        class DummyAsyncContextManager:
            async def __aenter__(self): return self
            async def __aexit__(self, exc_type, exc_val, exc_tb): pass
        mock_wait_for_domain.return_value = DummyAsyncContextManager()
        await crawler_instance.fetch_page(url, use_playwright=False)
    mock_wait_for_domain.assert_awaited_once_with("ratelimited-httpx.com")

@pytest.mark.asyncio
async def test_fetch_page_invalid_url_domain(crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    url = "mailto:test@example.com"
    html, status, final_url = await crawler_instance.fetch_page(url)
    assert html is None
    assert status == 0

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_captcha_detection_httpx(crawler_instance: AsyncWebCrawler, test_logger_instance_for_crawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    logger, temp_log_file, _ = test_logger_instance_for_crawler
    url = "http://captchasite-httpx.com"
    captcha_html = "<html><body>Please solve this reCAPTCHA to continue.</body></html>"
    respx.get(url).mock(return_value=httpx.Response(200, html=captcha_html))
    html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=False)
    assert status == 200
    assert html == captcha_html
    logger.complete()
    with open(temp_log_file, "r") as f: log_content = f.read()
    assert "Potential CAPTCHA detected" in log_content

@pytest.mark.asyncio
@patch('lead_gen_pipeline.crawler.AsyncWebCrawler._fetch_with_playwright', new_callable=AsyncMock)
async def test_fetch_page_captcha_detection_playwright(mock_internal_fetch_pw, crawler_instance: AsyncWebCrawler, test_logger_instance_for_crawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    logger, temp_log_file, _ = test_logger_instance_for_crawler
    url = "http://captchasite-pw.com"
    captcha_html = "<html><body>Please solve this reCAPTCHA to continue. Playwright</body></html>"
    mock_internal_fetch_pw.return_value = (captcha_html, 200, url)
    monkeypatch.setattr(global_app_settings.crawler, 'USE_PLAYWRIGHT_BY_DEFAULT', True)

    with patch('lead_gen_pipeline.utils.domain_rate_limiter.wait_for_domain', AsyncMock()) as mock_rate_limiter:
        class DummyAsyncContextManager:
            async def __aenter__(self): return self
            async def __aexit__(self, exc_type, exc_val, exc_tb): pass
        mock_rate_limiter.return_value = DummyAsyncContextManager()
        html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=True)
    assert status == 200
    assert html == captcha_html
    logger.complete()
    with open(temp_log_file, "r") as f: log_content = f.read()
    assert "Potential CAPTCHA detected" in log_content

@patch.object(AsyncWebCrawler, 'close_playwright_resources', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_crawler_close_calls_playwright_close(mock_close_pw_resources, crawler_instance):
    await crawler_instance.close()
    mock_close_pw_resources.assert_awaited_once()

