"""Tests for the async web crawler (HTTPX path, robots.txt, rate limiting).

Playwright is an optional extra, so the browser tests drive a mocked page and import the
Playwright error types from the crawler module (which provides fallbacks when the real
package is absent).
"""

import re
import urllib.robotparser
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import httpx
import pytest
import respx

from lead_gen_pipeline.config import settings as global_app_settings
from lead_gen_pipeline.crawler import (
    AsyncWebCrawler,
    PlaywrightBaseError,
    PlaywrightTimeoutError,
    RobotsTxtDisallowedError,
)


@pytest.fixture
def crawler(monkeypatch):
    AsyncWebCrawler._playwright_instance = None
    AsyncWebCrawler._browser = None
    instance = AsyncWebCrawler()
    monkeypatch.setattr(instance.settings, "RESPECT_ROBOTS_TXT", False)
    return instance


@pytest.fixture
def mock_pw_page():
    page = AsyncMock()
    context = AsyncMock()
    response = AsyncMock()
    page.goto = AsyncMock(return_value=response)
    page.content = AsyncMock(return_value="<html><body>PW</body></html>")
    type(page).url = PropertyMock(return_value="http://final.example/")
    type(response).status = PropertyMock(return_value=200)
    context.close = AsyncMock()
    return page, context, response


class _DummyCM:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return None


# HTTPX path
@respx.mock
@pytest.mark.asyncio
async def test_httpx_success(crawler):
    respx.get("http://ok.com").mock(
        return_value=httpx.Response(200, html="<html>ok</html>")
    )
    html, status, final = await crawler.fetch_page(
        "http://ok.com", use_playwright=False
    )
    assert status == 200
    assert html == "<html>ok</html>"
    assert final == "http://ok.com"


@respx.mock
@pytest.mark.asyncio
async def test_httpx_redirect(crawler):
    respx.get("http://from.com").mock(
        return_value=httpx.Response(301, headers={"Location": "http://to.com"})
    )
    respx.get("http://to.com").mock(return_value=httpx.Response(200, html="dest"))
    html, status, final = await crawler.fetch_page(
        "http://from.com", use_playwright=False
    )
    assert status == 200
    assert final == "http://to.com"


@respx.mock
@pytest.mark.asyncio
async def test_httpx_404_no_retry(crawler, monkeypatch):
    monkeypatch.setattr(global_app_settings.crawler, "MAX_RETRIES", 0)
    respx.get("http://nf.com").mock(return_value=httpx.Response(404))
    html, status, _ = await crawler.fetch_page("http://nf.com", use_playwright=False)
    assert status == 404
    assert html is None


@respx.mock
@pytest.mark.asyncio
async def test_httpx_timeout(crawler, monkeypatch):
    monkeypatch.setattr(global_app_settings.crawler, "MAX_RETRIES", 0)
    req = httpx.Request("GET", "http://slow.com")
    respx.get("http://slow.com").mock(
        side_effect=httpx.TimeoutException("t", request=req)
    )
    html, status, _ = await crawler.fetch_page("http://slow.com", use_playwright=False)
    assert status == 408
    assert html is None


@respx.mock
@pytest.mark.asyncio
async def test_httpx_network_error(crawler, monkeypatch):
    monkeypatch.setattr(global_app_settings.crawler, "MAX_RETRIES", 0)
    req = httpx.Request("GET", "http://dead.com")
    respx.get("http://dead.com").mock(side_effect=httpx.ConnectError("x", request=req))
    html, status, _ = await crawler.fetch_page("http://dead.com", use_playwright=False)
    assert status == 599
    assert html is None


@respx.mock
@pytest.mark.asyncio
async def test_httpx_retry_then_success(crawler, monkeypatch):
    monkeypatch.setattr(global_app_settings.crawler, "MAX_RETRIES", 1)
    respx.get("http://retry.com").mock(
        side_effect=[httpx.Response(500), httpx.Response(200, html="recovered")]
    )
    with patch("lead_gen_pipeline.utils.asyncio.sleep", AsyncMock()):
        html, status, _ = await crawler.fetch_page(
            "http://retry.com", use_playwright=False
        )
    assert status == 200
    assert html == "recovered"


@pytest.mark.asyncio
async def test_invalid_url(crawler):
    html, status, _ = await crawler.fetch_page("mailto:x@y.com")
    assert html is None
    assert status == 0


# Playwright path (mocked)
@pytest.mark.asyncio
@patch.object(AsyncWebCrawler, "_get_playwright_page", new_callable=AsyncMock)
async def test_playwright_success(mock_get_page, crawler, mock_pw_page):
    page, context, _ = mock_pw_page
    mock_get_page.return_value = (page, context)
    html, status, final = await crawler._fetch_with_playwright("http://pw.com", 30000)
    assert status == 200
    assert html == "<html><body>PW</body></html>"
    assert final == "http://final.example/"
    context.close.assert_awaited_once()


@pytest.mark.asyncio
@patch.object(AsyncWebCrawler, "_get_playwright_page", new_callable=AsyncMock)
async def test_playwright_timeout_reraises(mock_get_page, crawler, mock_pw_page):
    page, context, _ = mock_pw_page
    mock_get_page.return_value = (page, context)
    page.goto.side_effect = PlaywrightTimeoutError("timed out")
    with pytest.raises(PlaywrightTimeoutError):
        await crawler._fetch_with_playwright("http://pw.com", 100)
    context.close.assert_awaited_once()


@pytest.mark.asyncio
@patch.object(AsyncWebCrawler, "_get_playwright_page", new_callable=AsyncMock)
async def test_playwright_no_response(mock_get_page, crawler, mock_pw_page):
    page, context, _ = mock_pw_page
    mock_get_page.return_value = (page, context)
    page.goto.return_value = None
    with pytest.raises(PlaywrightBaseError, match="return a response object"):
        await crawler._fetch_with_playwright("http://pw.com", 30000)


@pytest.mark.asyncio
@patch.object(AsyncWebCrawler, "_fetch_with_playwright", new_callable=AsyncMock)
async def test_fetch_page_uses_playwright(mock_fetch, crawler):
    mock_fetch.return_value = ("<html>pw</html>", 200, "http://pw.final")
    with patch(
        "lead_gen_pipeline.utils.domain_rate_limiter.wait_for_domain",
        AsyncMock(return_value=_DummyCM()),
    ):
        html, status, _ = await crawler.fetch_page("http://pw.com", use_playwright=True)
    assert status == 200
    assert html == "<html>pw</html>"


# robots.txt
@respx.mock
@pytest.mark.asyncio
async def test_robots_parsed_https(crawler):
    respx.get("https://e.com/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow:")
    )
    parser = await crawler._fetch_and_parse_robots_txt("e.com")
    assert isinstance(parser, urllib.robotparser.RobotFileParser)
    assert parser.can_fetch("*", "https://e.com/any") is True


@respx.mock
@pytest.mark.asyncio
async def test_robots_http_fallback(crawler):
    respx.get("https://fb.com/robots.txt").mock(return_value=httpx.Response(500))
    respx.get("http://fb.com/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /private/")
    )
    parser = await crawler._fetch_and_parse_robots_txt("fb.com")
    assert parser is not None
    assert parser.can_fetch("*", "http://fb.com/private/x") is False


@respx.mock
@pytest.mark.asyncio
async def test_robots_404_is_permissive(crawler):
    respx.get("https://nr.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("http://nr.com/robots.txt").mock(return_value=httpx.Response(404))
    parser = await crawler._fetch_and_parse_robots_txt("nr.com")
    assert parser is None


@pytest.mark.asyncio
async def test_robots_parser_is_cached(crawler, monkeypatch):
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(["User-agent: *", "Disallow:"])
    fetch = AsyncMock(return_value=parser)
    monkeypatch.setattr(crawler, "_fetch_and_parse_robots_txt", fetch)

    await crawler._get_robots_parser("c.com")
    await crawler._get_robots_parser("c.com")
    fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_robots_disallowed_raises(crawler, monkeypatch):
    url = "http://block.com/secret"
    ua = crawler.settings.ROBOTS_TXT_USER_AGENT
    parser = MagicMock(spec=urllib.robotparser.RobotFileParser)
    parser.can_fetch.return_value = False
    monkeypatch.setattr(crawler, "_get_robots_parser", AsyncMock(return_value=parser))

    expected = f"URL '{url}' is disallowed by robots.txt for user-agent '{ua}'."
    with pytest.raises(RobotsTxtDisallowedError, match=re.escape(expected)):
        await crawler._check_robots_txt(url)


@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_blocks_disallowed(crawler, monkeypatch):
    monkeypatch.setattr(crawler.settings, "RESPECT_ROBOTS_TXT", True)
    monkeypatch.setattr(crawler.settings, "ROBOTS_TXT_USER_AGENT", "TestBot")
    respx.get("https://r.com/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: TestBot\nDisallow: /no.html")
    )
    respx.get("http://r.com/robots.txt").mock(return_value=httpx.Response(404))
    blocked = respx.get("http://r.com/no.html")
    html, status, _ = await crawler.fetch_page(
        "http://r.com/no.html", use_playwright=False
    )
    assert html is None
    assert status == 403
    assert blocked.call_count == 0


# misc
@respx.mock
@pytest.mark.asyncio
async def test_captcha_detection_logs(crawler, tmp_path):
    from lead_gen_pipeline.config import LoggingSettings
    from lead_gen_pipeline.utils import setup_logger

    log_file = tmp_path / "c.log"
    setup_logger(
        LoggingSettings(
            LOG_LEVEL="WARNING",
            LOG_FILE_PATH=log_file,
            ERROR_LOG_FILE_PATH=tmp_path / "e.log",
        )
    )
    respx.get("http://captcha.com").mock(
        return_value=httpx.Response(200, html="Please solve this reCAPTCHA to continue")
    )
    await crawler.fetch_page("http://captcha.com", use_playwright=False)
    from lead_gen_pipeline.utils import logger

    logger.complete()
    assert "Potential CAPTCHA detected" in log_file.read_text()
    setup_logger(global_app_settings.logging)


@pytest.mark.asyncio
async def test_close_clears_cache(crawler, monkeypatch):
    crawler._robots_parsers_cache["d.com"] = None
    monkeypatch.setattr(AsyncWebCrawler, "close_playwright_resources", AsyncMock())
    await crawler.close()
    assert not crawler._robots_parsers_cache
    AsyncWebCrawler.close_playwright_resources.assert_awaited_once()
