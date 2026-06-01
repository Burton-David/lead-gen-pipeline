"""Tests for the async database layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select, text

from lead_gen_pipeline import database
from lead_gen_pipeline.database import (
    get_async_session_local,
    save_lead,
)
from lead_gen_pipeline.models import Lead


@pytest.mark.asyncio
async def test_init_db_creates_leads_table(initialized_db):
    async with get_async_session_local()() as session:
        result = await session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='leads'")
        )
        assert result.scalar_one_or_none() == "leads"


@pytest.mark.asyncio
async def test_save_lead_commits_with_local_session(initialized_db):
    lead = await save_lead(
        {
            "company_name": "Tech Corp",
            "website": "https://techcorp.com",
            "scraped_from_url": "https://techcorp.com/about",
            "phone_numbers": ["+18005550001"],
            "emails": ["contact@techcorp.com"],
        }
    )
    assert lead is not None and lead.id is not None

    async with get_async_session_local()() as session:
        fetched = await session.get(Lead, lead.id)
        assert fetched is not None
        assert fetched.company_name == "Tech Corp"
        assert fetched.emails == ["contact@techcorp.com"]


@pytest.mark.asyncio
async def test_save_lead_with_external_session_requires_commit(initialized_db):
    async with get_async_session_local()() as session:
        lead = await save_lead(
            {"scraped_from_url": "https://ext.co", "company_name": "Ext"},
            db_session=session,
        )
        assert lead is not None and lead.id is not None
        await session.commit()

    async with get_async_session_local()() as other:
        assert (await other.get(Lead, lead.id)).company_name == "Ext"


@pytest.mark.asyncio
async def test_save_lead_rejects_unknown_columns(initialized_db):
    lead = await save_lead({"scraped_from_url": "https://x.co", "not_a_column": "boom"})
    assert lead is None


@pytest.mark.asyncio
async def test_save_lead_rolls_back_on_commit_error(monkeypatch, initialized_db):
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock(side_effect=RuntimeError("commit failed"))
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()

    monkeypatch.setattr(database, "get_async_session_local", lambda: (lambda: session))

    result = await save_lead({"scraped_from_url": "https://err.co"})

    assert result is None
    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_lead_ordering_query(initialized_db):
    for i in range(3):
        await save_lead(
            {"scraped_from_url": f"https://s{i}.co", "company_name": f"C{i}"}
        )
    async with get_async_session_local()() as session:
        rows = (await session.execute(select(Lead))).scalars().all()
        assert len(rows) == 3
