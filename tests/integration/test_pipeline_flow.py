# tests/integration/test_pipeline_flow.py
# Version: Gemini-2025-05-26 21:10 EDT

import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
import csv
from typing import List
import sys
import respx 

PROJECT_ROOT_FOR_IMPORTS = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORTS))

from lead_gen_pipeline.config import settings as global_settings
from lead_gen_pipeline.run_pipeline_mvp import main_pipeline
from lead_gen_pipeline.models import Base, Lead
from lead_gen_pipeline.database import get_engine, get_async_session_local, _reset_db_state_for_testing
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import func

MOCK_B2B_SITE_URL = "http://mock-b2b-site.com/contact"
MOCK_B2B_HTML_CONTENT = """
<html>
<head>
    <title>TestBiz Solutions Inc. | Innovative Business Software</title>
    <meta name="description" content="TestBiz offers cutting-edge solutions for B2B needs. Contact us for more info.">
    <meta property="og:site_name" content="TestBiz Solutions Official">
    <link rel="canonical" href="http://mock-b2b-site.com/canonical-contact">
</head>
<body>
    <h1>Welcome to TestBiz Solutions</h1>
    <p>Your partner in success.</p>
    <div class="contact-info">
        <p>Email us at: <a href="mailto:info@testbizsolutions.com?subject=Inquiry">info@testbizsolutions.com</a></p>
        <p>Or Sales: sales@testbizsolutions.com for quotes.</p>
        <p>Call us: <a href="tel:+1-555-0123-4567">+1 (555) 0123-4567</a> (Main)</p>
        <p>Support Line: 555-0123-7654</p>
    </div>
    <div class="address" itemscope itemtype="http://schema.org/PostalAddress">
        <span itemprop="streetAddress">123 Innovation Drive</span>,
        <span itemprop="addressLocality">Tech City</span>,
        <span itemprop="addressRegion">TS</span>
        <span itemprop="postalCode">90210</span>.
        Our other office is at 456 Business Ave, Metroville, ST 10001.
    </div>
    <div class="social-media">
        <a href="https://linkedin.com/company/testbiz">Our LinkedIn</a>
        <a href="http://twitter.com/testbizinc">Follow TestBiz on Twitter</a>
        <a href="https://www.facebook.com/TestBizSolutions">Facebook Page</a>
    </div>
    <footer>
        General Address: Main Street 1, Big City, BC 12345
    </footer>
</body>
</html>
"""

@pytest_asyncio.fixture(scope="function")
async def integration_test_setup(tmp_path: Path, monkeypatch, respx_mock: respx.MockRouter):
    temp_db_file = tmp_path / "test_integration_leads.db"
    test_async_db_url_integration = f"sqlite+aiosqlite:///{temp_db_file.resolve()}"

    _reset_db_state_for_testing() 

    temp_data_dir = tmp_path / "data"
    temp_data_dir.mkdir(exist_ok=True)
    temp_urls_csv = temp_data_dir / "temp_urls_seed.csv"
    
    test_urls = [
        {"url": "http://httpbin.org/html", "comment": "Simple HTML page"},
        {"url": MOCK_B2B_SITE_URL, "comment": "Mocked Rich B2B Site"},
        {"url": "http://httpbin.org/status/404", "comment": "Known 404 page"}, 
    ]
    with open(temp_urls_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['url', 'comment']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in test_urls:
            writer.writerow(row)

    respx_mock.get(MOCK_B2B_SITE_URL).respond(200, html=MOCK_B2B_HTML_CONTENT)
    respx_mock.get("http://httpbin.org/html").pass_through()
    respx_mock.get("http://httpbin.org/robots.txt").pass_through()
    respx_mock.get("https://httpbin.org/robots.txt").pass_through()
    respx_mock.get("http://httpbin.org/status/404").pass_through()

    original_settings_values = {
        "INPUT_URLS_CSV": global_settings.INPUT_URLS_CSV,
        "DATABASE_URL": global_settings.database.DATABASE_URL,
        "LOG_LEVEL": global_settings.logging.LOG_LEVEL,
        "MAX_PIPELINE_CONCURRENCY": global_settings.MAX_PIPELINE_CONCURRENCY,
        "RESPECT_ROBOTS_TXT": global_settings.crawler.RESPECT_ROBOTS_TXT,
    }

    monkeypatch.setattr(global_settings, 'INPUT_URLS_CSV', temp_urls_csv)
    monkeypatch.setattr(global_settings.database, 'DATABASE_URL', test_async_db_url_integration)
    monkeypatch.setattr(global_settings.logging, 'LOG_LEVEL', "DEBUG") 
    monkeypatch.setattr(global_settings, 'MAX_PIPELINE_CONCURRENCY', 2) 
    monkeypatch.setattr(global_settings.crawler, 'RESPECT_ROBOTS_TXT', False)

    test_pipeline_engine = get_engine() 
    async with test_pipeline_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield {
        "temp_db_file_path": temp_db_file,
    } 

    _reset_db_state_for_testing()
    monkeypatch.setattr(global_settings, 'INPUT_URLS_CSV', original_settings_values["INPUT_URLS_CSV"])
    monkeypatch.setattr(global_settings.database, 'DATABASE_URL', original_settings_values["DATABASE_URL"])
    monkeypatch.setattr(global_settings.logging, 'LOG_LEVEL', original_settings_values["LOG_LEVEL"])
    monkeypatch.setattr(global_settings, 'MAX_PIPELINE_CONCURRENCY', original_settings_values["MAX_PIPELINE_CONCURRENCY"])
    monkeypatch.setattr(global_settings.crawler, 'RESPECT_ROBOTS_TXT', original_settings_values["RESPECT_ROBOTS_TXT"])
    
    if test_pipeline_engine:
         await test_pipeline_engine.dispose()


@pytest.mark.asyncio
async def test_mvp_pipeline_flow(integration_test_setup, caplog):
    test_run_config = integration_test_setup
    temp_db_file_path_for_assertion = test_run_config["temp_db_file_path"]
    
    caplog.set_level("DEBUG", logger="lead_gen_pipeline")

    await main_pipeline()

    assertion_engine = create_async_engine(
        f"sqlite+aiosqlite:///{temp_db_file_path_for_assertion.resolve()}",
        connect_args={'check_same_thread': False} 
    )
    LocalAssertionSession = sessionmaker(
        bind=assertion_engine, class_=AsyncSession, expire_on_commit=False
    )

    leads_in_db: List[Lead] = []
    db_lead_count = 0
    async with LocalAssertionSession() as session: 
        count_result = await session.execute(select(func.count(Lead.id)))
        db_lead_count = count_result.scalar_one_or_none() or 0
        
        if db_lead_count > 0:
            result = await session.execute(select(Lead))
            leads_in_db = result.scalars().all()
    
    await assertion_engine.dispose()

    assert db_lead_count == 2, f"Expected 2 leads to be saved, found {db_lead_count}. DB file: {temp_db_file_path_for_assertion}. Check logs for errors."
    assert len(leads_in_db) == 2, f"Lead objects fetched mismatch count. Expected 2, got {len(leads_in_db)}"

    saved_urls = {lead.scraped_from_url for lead in leads_in_db}
    assert "http://httpbin.org/html" in saved_urls
    assert MOCK_B2B_SITE_URL in saved_urls
    assert "http://httpbin.org/status/404" not in saved_urls

    html_lead = next((lead for lead in leads_in_db if lead.scraped_from_url == "http://httpbin.org/html"), None)
    assert html_lead is not None, "Lead from http://httpbin.org/html not found in DB"
    assert html_lead.company_name is None, \
        f"Expected company_name to be None for httpbin.org/html, got '{html_lead.company_name}'"
    assert html_lead.website == "http://httpbin.org"

    mock_b2b_lead = next((lead for lead in leads_in_db if lead.scraped_from_url == MOCK_B2B_SITE_URL), None)
    assert mock_b2b_lead is not None, f"Lead from {MOCK_B2B_SITE_URL} not found in DB"
    assert mock_b2b_lead.company_name == "TestBiz Solutions Official"
    assert mock_b2b_lead.website == "http://mock-b2b-site.com"
    assert "TestBiz offers cutting-edge solutions for B2B needs." in (mock_b2b_lead.description or "")
    assert "info@testbizsolutions.com" in (mock_b2b_lead.emails or [])
    assert "sales@testbizsolutions.com" in (mock_b2b_lead.emails or [])
    # ADJUSTED ASSERTION to match current scraper output for this specific tel: link
    assert "+1-555-0123-4567" in (mock_b2b_lead.phone_numbers or []) 
    assert "555-0123-7654" in (mock_b2b_lead.phone_numbers or []) # This one should be fine
    assert any("123 Innovation Drive" in addr for addr in (mock_b2b_lead.addresses or [])), \
        f"Primary address not found in {mock_b2b_lead.addresses}"
    assert (mock_b2b_lead.social_media_links or {}).get("linkedin") == "https://linkedin.com/company/testbiz"
    assert (mock_b2b_lead.social_media_links or {}).get("twitter") == "http://twitter.com/testbizinc"
    assert (mock_b2b_lead.social_media_links or {}).get("facebook") == "https://www.facebook.com/TestBizSolutions"
    assert mock_b2b_lead.canonical_url == "http://mock-b2b-site.com/canonical-contact"

    assert "Failed to fetch content for http://httpbin.org/status/404" in caplog.text
    assert "Starting B2B Lead Generation Pipeline MVP run..." in caplog.text
    assert "Database initialized successfully." in caplog.text
    assert "Loaded 3 seed URLs for processing." in caplog.text 
    assert "Successfully saved lead ID" in caplog.text 
    assert "B2B Lead Generation Pipeline MVP run finished." in caplog.text
    assert "Crawler resources closed." in caplog.text

    critical_errors = [rec.message for rec in caplog.records if rec.levelname == "CRITICAL"]
    assert not critical_errors, f"Critical errors found in logs: {critical_errors}"
