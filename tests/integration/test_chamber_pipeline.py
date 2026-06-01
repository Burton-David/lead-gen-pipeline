"""End-to-end test of the agentic chamber pipeline with a fake LLM backend.

Exercises the full path - directory discovery, listing extraction, deduplication, and
bulk persistence - without the network or the 4 GB model, by injecting a fake crawler and
a fake-backed LLM processor.
"""

import json

import pytest
from sqlalchemy import select

from lead_gen_pipeline.bulk_database import BulkDatabaseProcessor
from lead_gen_pipeline.chamber_parser import ChamberDirectoryParser
from lead_gen_pipeline.database import get_async_session_local
from lead_gen_pipeline.llm_processor import create_llm_processor
from lead_gen_pipeline.models import Lead

CHAMBER_URL = "https://chamber.org"
DIRECTORY_URL = "https://chamber.org/members"

CHAMBER_HTML = """
<html><head><meta property="og:site_name" content="Springfield Chamber"></head>
<body><a href="/members">Member Directory</a></body></html>
"""
DIRECTORY_HTML = "<html><body>directory listing</body></html>"


class FakeCrawler:
    """Returns canned HTML for any URL; records the URLs it was asked to fetch."""

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.fetched: list[str] = []

    async def fetch_page(self, url, use_playwright=None):
        self.fetched.append(url)
        return self.pages.get(url, DIRECTORY_HTML), 200, url

    async def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_chamber_flow_extracts_dedupes_and_persists(initialized_db):
    nav = json.dumps({"navigation_links": [DIRECTORY_URL], "confidence": 90})
    listings = json.dumps(
        {
            "business_listings": [
                {"name": "Acme Co", "website": "http://acme.com", "phone": "555-1000"},
                {"name": "Acme Co", "website": "http://acme.com"},  # duplicate
                {"name": "Beta LLC", "email": "hi@beta.com"},
            ],
            "pagination": {"next_page_url": None, "has_more": False},
        }
    )

    crawler = FakeCrawler({CHAMBER_URL: CHAMBER_HTML, DIRECTORY_URL: DIRECTORY_HTML})
    processor = create_llm_processor(
        backend=_FixedBackend(nav_json=nav, listing_json=listings)
    )
    parser = ChamberDirectoryParser(crawler=crawler, llm_processor=processor)
    parser.delay_between_requests = 0  # no inter-request sleep in tests
    assert await parser.initialize() is True

    result = await parser.parse_chamber_directory(CHAMBER_URL)

    assert result.success is True
    assert result.chamber_info["name"] == "Springfield Chamber"
    # Acme deduplicated -> 2 unique businesses.
    assert result.total_businesses_found == 2

    bulk = BulkDatabaseProcessor(batch_size=100)
    await bulk.bulk_insert_chamber_results([result])

    async with get_async_session_local()() as session:
        leads = (await session.execute(select(Lead))).scalars().all()

    names = {lead.company_name for lead in leads}
    assert names == {"Acme Co", "Beta LLC"}
    assert all(lead.chamber_name == "Springfield Chamber" for lead in leads)


@pytest.mark.asyncio
async def test_chamber_flow_falls_back_when_no_links(initialized_db):
    # LLM returns no navigation links: the parser falls back to common directory paths.
    crawler = FakeCrawler({CHAMBER_URL: CHAMBER_HTML})
    processor = create_llm_processor(
        backend=_FixedBackend(
            nav_json=json.dumps({"navigation_links": []}),
            listing_json=json.dumps({"business_listings": [], "pagination": {}}),
        )
    )
    parser = ChamberDirectoryParser(crawler=crawler, llm_processor=processor)
    parser.delay_between_requests = 0  # no inter-request sleep in tests
    await parser.initialize()
    result = await parser.parse_chamber_directory(CHAMBER_URL)

    assert result.success is True
    # Fallback directory paths were attempted.
    assert any("/directory" in u or "/members" in u for u in crawler.fetched)


class _FixedBackend:
    def __init__(self, nav_json: str, listing_json: str) -> None:
        self.nav_json = nav_json
        self.listing_json = listing_json

    def ensure_ready(self) -> bool:
        return True

    def generate(self, prompt: str, *, max_tokens: int, temperature: float) -> str:
        return self.listing_json if "Extract business data" in prompt else self.nav_json
