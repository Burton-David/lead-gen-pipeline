"""Tests for the LLM processor: JSON repair, preprocessing, and extraction.

These run against a deterministic fake backend, so no model is required.
"""

import json

import pytest

from lead_gen_pipeline.llm_processor import LLMProcessor, create_llm_processor

CHAMBER_HTML = """
<html><body>
  <h1>Springfield Chamber of Commerce</h1>
  <a href="/members">Member Directory</a>
  <a href="https://chamber.org/businesses">Businesses</a>
</body></html>
"""

DIRECTORY_HTML = """
<html><body>
  <div class="listing"><h3>Acme Co</h3><a href="http://acme.com">site</a></div>
  <div class="listing"><h3>Beta LLC</h3></div>
</body></html>
"""


def test_robust_json_parse_plain():
    proc = LLMProcessor(backend=object())  # backend unused for this method
    assert proc._robust_json_parse('{"a": 1}') == {"a": 1}


def test_robust_json_parse_strips_markdown_fence():
    proc = LLMProcessor(backend=object())
    fenced = '```json\n{"navigation_links": ["/x"]}\n```'
    assert proc._robust_json_parse(fenced) == {"navigation_links": ["/x"]}


def test_robust_json_parse_repairs_malformed():
    proc = LLMProcessor(backend=object())
    # Trailing comma + missing closing brace: invalid JSON, repairable.
    repaired = proc._robust_json_parse('{"navigation_links": ["/a", "/b",]')
    assert repaired == {"navigation_links": ["/a", "/b"]}


def test_robust_json_parse_empty_returns_none():
    proc = LLMProcessor(backend=object())
    assert proc._robust_json_parse("") is None
    assert proc._robust_json_parse("   ") is None


def test_html_to_markdown_reduces_to_text():
    proc = LLMProcessor(backend=object())
    md = proc._html_to_markdown("<h1>Title</h1><p>Body text</p>")
    assert "Title" in md
    assert "Body text" in md
    assert "<h1>" not in md


def test_preprocess_truncates_and_caches():
    proc = LLMProcessor(backend=object())
    proc.settings.CONTEXT_SIZE = 10  # max_chars = 30
    big = "<p>" + "x" * 500 + "</p>"
    out = proc._preprocess_chamber_page(big)
    assert out.endswith("[Content truncated]")
    # Second call hits the cache and returns the identical result.
    assert proc._preprocess_chamber_page(big) == out


@pytest.mark.asyncio
async def test_find_directory_links_absolutizes(make_backend):
    nav = json.dumps(
        {"navigation_links": ["/members", "https://chamber.org/businesses"]}
    )
    proc = create_llm_processor(backend=make_backend(nav_json=nav))
    links = await proc.find_directory_links(CHAMBER_HTML, "https://chamber.org")
    assert "https://chamber.org/members" in links
    assert "https://chamber.org/businesses" in links


@pytest.mark.asyncio
async def test_extract_business_listings_cleans_and_paginates(make_backend):
    listing = json.dumps(
        {
            "business_listings": [
                {"name": "  Acme Co ", "website": "http://acme.com"},
                {"name": "", "website": ""},  # dropped: no name or website
                {"name": "Beta LLC", "phone": "555-1234"},
            ],
            "pagination": {"next_page_url": "/page/2"},
        }
    )
    proc = create_llm_processor(backend=make_backend(listing_json=listing))
    businesses, next_url = await proc.extract_business_listings(
        DIRECTORY_HTML, "https://chamber.org/members"
    )
    assert [b["name"] for b in businesses] == ["Acme Co", "Beta LLC"]
    assert businesses[0]["source_url"] == "https://chamber.org/members"
    assert next_url == "https://chamber.org/page/2"


@pytest.mark.asyncio
async def test_extract_recovers_from_malformed_json(make_backend):
    # Missing closing brace; json-repair should still recover the listing.
    listing = '{"business_listings": [{"name": "Acme", "website": "http://acme.com"}]'
    proc = create_llm_processor(backend=make_backend(listing_json=listing))
    businesses, _ = await proc.extract_business_listings(
        DIRECTORY_HTML, "https://c.org"
    )
    assert businesses and businesses[0]["name"] == "Acme"


@pytest.mark.asyncio
async def test_initialize_uses_backend_ready(fake_backend):
    proc = LLMProcessor(backend=fake_backend)
    assert await proc.initialize() is True
    assert fake_backend.ready_calls == 1
