"""End-to-end test of the single-page MVP pipeline.

All network is mocked with respx, so the test is deterministic and offline.
"""

import csv

import httpx
import pytest
import respx
from sqlalchemy import select

from lead_gen_pipeline.config import settings
from lead_gen_pipeline.database import get_async_session_local
from lead_gen_pipeline.models import Lead
from lead_gen_pipeline.run_pipeline_mvp import main_pipeline

B2B_URL = "http://b2b-co.com/contact"
SIMPLE_URL = "http://simple-co.com/"
MISSING_URL = "http://missing-co.com/404"

B2B_HTML = """
<html>
<head>
    <title>TestBiz Solutions Inc. | Software</title>
    <meta name="description" content="B2B software solutions.">
    <meta property="og:site_name" content="TestBiz Solutions Official">
    <link rel="canonical" href="http://b2b-co.com/canonical">
</head>
<body>
    <p>Email: <a href="mailto:info@b2b-co.com">info@b2b-co.com</a></p>
    <p>Phone: <a href="tel:+13035560123">(303) 556-0123</a></p>
    <a href="https://linkedin.com/company/testbiz">LinkedIn</a>
</body>
</html>
"""

SIMPLE_HTML = """
<html><head><title>Simple Co</title></head>
<body><p>Reach us at <a href="mailto:hi@simple-co.com">hi@simple-co.com</a></p></body></html>
"""


@pytest.fixture
def seed_csv(tmp_path, monkeypatch):
    csv_path = tmp_path / "seed.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["url"])
        writer.writerow([B2B_URL])
        writer.writerow([SIMPLE_URL])
        writer.writerow([MISSING_URL])
    monkeypatch.setattr(settings, "INPUT_URLS_CSV", csv_path)
    monkeypatch.setattr(settings.crawler, "RESPECT_ROBOTS_TXT", False)
    monkeypatch.setattr(settings.crawler, "USE_PLAYWRIGHT_BY_DEFAULT", False)
    monkeypatch.setattr(settings, "MAX_PIPELINE_CONCURRENCY", 2)
    # The rate limiter is a process-wide singleton; zero the delay so tests that reuse
    # domains stay fast and isolated.
    monkeypatch.setattr(settings.crawler, "MIN_DELAY_PER_DOMAIN_SECONDS", 0.0)
    monkeypatch.setattr(settings.crawler, "MAX_DELAY_PER_DOMAIN_SECONDS", 0.0)
    monkeypatch.setattr(settings.crawler, "MAX_RETRIES", 0)  # no backoff in tests
    return csv_path


@respx.mock
@pytest.mark.asyncio
async def test_mvp_pipeline_end_to_end(seed_csv, initialized_db):
    respx.get(B2B_URL).mock(return_value=httpx.Response(200, html=B2B_HTML))
    respx.get(SIMPLE_URL).mock(return_value=httpx.Response(200, html=SIMPLE_HTML))
    respx.get(MISSING_URL).mock(return_value=httpx.Response(404))

    await main_pipeline()

    async with get_async_session_local()() as session:
        leads = (await session.execute(select(Lead))).scalars().all()

    saved_urls = {lead.scraped_from_url for lead in leads}
    assert saved_urls == {B2B_URL, SIMPLE_URL}  # 404 skipped
    assert MISSING_URL not in saved_urls

    b2b = next(lead for lead in leads if lead.scraped_from_url == B2B_URL)
    assert b2b.company_name == "TestBiz Solutions Official"
    assert b2b.website == "http://b2b-co.com"
    assert b2b.canonical_url == "http://b2b-co.com/canonical"
    assert "info@b2b-co.com" in (b2b.emails or [])
    assert "+13035560123" in (b2b.phone_numbers or [])
    assert (b2b.social_media_links or {}).get("linkedin") == (
        "https://linkedin.com/company/testbiz"
    )


@respx.mock
@pytest.mark.asyncio
async def test_mvp_pipeline_handles_all_failures(seed_csv, initialized_db):
    # Every URL fails; the pipeline should complete and save nothing.
    respx.get(B2B_URL).mock(return_value=httpx.Response(500))
    respx.get(SIMPLE_URL).mock(return_value=httpx.Response(503))
    respx.get(MISSING_URL).mock(return_value=httpx.Response(404))

    await main_pipeline()

    async with get_async_session_local()() as session:
        leads = (await session.execute(select(Lead))).scalars().all()
    assert leads == []
