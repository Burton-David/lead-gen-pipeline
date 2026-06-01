"""Tests for high-throughput bulk database operations."""

import pytest
from sqlalchemy import select

from lead_gen_pipeline.bulk_database import BulkDatabaseProcessor
from lead_gen_pipeline.database import get_async_session_local
from lead_gen_pipeline.models import Lead

CHAMBER_INFO = {"name": "Springfield Chamber", "website": "https://chamber.org"}


def test_normalize_business_data_maps_fields():
    proc = BulkDatabaseProcessor.__new__(BulkDatabaseProcessor)  # no DB needed
    record = proc._normalize_business_data(
        {
            "name": "Acme Co",
            "website": "acme.com",
            "phone": "+18005551212",
            "email": "info@acme.com",
            "industry": "Manufacturing",
            "source_url": "https://chamber.org/members",
        },
        CHAMBER_INFO,
    )
    assert record["company_name"] == "Acme Co"
    assert record["website"] == "https://acme.com"  # scheme added
    assert record["phone_numbers"] == ["+18005551212"]
    assert record["emails"] == ["info@acme.com"]
    assert record["industry_tags"] == ["Manufacturing"]
    assert record["chamber_name"] == "Springfield Chamber"
    assert "description" not in record  # None values dropped


def test_business_hash_is_stable_and_case_insensitive():
    proc = BulkDatabaseProcessor.__new__(BulkDatabaseProcessor)
    a = proc._create_business_hash(
        {"company_name": "Acme", "website": "http://acme.com"}
    )
    b = proc._create_business_hash(
        {"company_name": "ACME", "website": "HTTP://ACME.COM"}
    )
    assert a == b


@pytest.mark.asyncio
async def test_bulk_insert_dedupes_and_persists(initialized_db):
    proc = BulkDatabaseProcessor(batch_size=10)
    businesses = [
        {"name": "Acme Co", "website": "http://acme.com", "source_url": "u"},
        {"name": "Acme Co", "website": "http://acme.com", "source_url": "u"},  # dup
        {"name": "Beta LLC", "website": "http://beta.com", "source_url": "u"},
    ]
    stats = await proc.bulk_insert_businesses(businesses, CHAMBER_INFO)
    assert stats.successful_inserts == 2
    assert stats.duplicates_skipped == 1

    async with get_async_session_local()() as session:
        rows = (await session.execute(select(Lead))).scalars().all()
        assert {r.company_name for r in rows} == {"Acme Co", "Beta LLC"}


@pytest.mark.asyncio
async def test_bulk_insert_updates_existing(initialized_db):
    proc = BulkDatabaseProcessor(batch_size=10)
    await proc.bulk_insert_businesses(
        [{"name": "Acme Co", "website": "http://acme.com", "source_url": "u"}],
        CHAMBER_INFO,
    )
    # New processor (fresh dedup cache) with an updated email for the same business.
    proc2 = BulkDatabaseProcessor(batch_size=10)
    stats = await proc2.bulk_insert_businesses(
        [
            {
                "name": "Acme Co",
                "website": "http://acme.com",
                "email": "new@acme.com",
                "source_url": "u",
            }
        ],
        CHAMBER_INFO,
        update_existing=True,
    )
    assert stats.successful_updates == 1

    async with get_async_session_local()() as session:
        rows = (await session.execute(select(Lead))).scalars().all()
        assert len(rows) == 1
        assert rows[0].emails == ["new@acme.com"]


@pytest.mark.asyncio
async def test_database_statistics(initialized_db):
    proc = BulkDatabaseProcessor(batch_size=10)
    await proc.bulk_insert_businesses(
        [
            {
                "name": "A",
                "website": "http://a.com",
                "email": "a@a.com",
                "source_url": "u",
            },
            {"name": "B", "website": "http://b.com", "source_url": "u"},
        ],
        CHAMBER_INFO,
    )
    stats = await proc.get_database_statistics()
    assert stats["total_leads"] == 2
    assert stats["leads_with_emails"] == 1
    assert stats["leads_with_websites"] == 2


@pytest.mark.asyncio
async def test_bulk_insert_empty_is_noop(initialized_db):
    proc = BulkDatabaseProcessor(batch_size=10)
    stats = await proc.bulk_insert_businesses([], CHAMBER_INFO)
    assert stats.total_attempted == 0
    assert stats.successful_inserts == 0
