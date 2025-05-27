# tests/unit/test_database.py
# Version: Gemini-2025-05-26 14:55 EDT

import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock

PROJECT_ROOT_FOR_IMPORTS = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORTS))

from lead_gen_pipeline.models import Base, Lead
from lead_gen_pipeline.database import init_db, save_lead 
from lead_gen_pipeline.config import settings

TEST_ASYNC_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="function", autouse=True)
async def override_engine_and_init_db(monkeypatch):
    """
    Override the global engine and sessionmaker for test isolation.
    Ensures a clean database with tables created for each test function.
    """
    test_engine = create_async_engine(TEST_ASYNC_DB_URL, echo=False)
    TestAsyncSessionLocal = sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    monkeypatch.setattr("lead_gen_pipeline.database.engine", test_engine)
    monkeypatch.setattr("lead_gen_pipeline.database.AsyncSessionLocal", TestAsyncSessionLocal)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) 
        await conn.run_sync(Base.metadata.create_all) 
    
    yield 

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_init_db_creates_tables():
    """Test that init_db creates (or confirms existence of) the 'leads' table."""
    from lead_gen_pipeline.database import AsyncSessionLocal as PatchedAsyncSessionLocal

    await init_db() 

    async with PatchedAsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='leads';"))
            table = result.fetchone()
            assert table is not None, "The 'leads' table was not found after calling init_db."
            assert table[0] == "leads"

@pytest.mark.asyncio
async def test_save_lead_success():
    """Test saving a valid lead to the database. Assumes tables exist from fixture."""
    from lead_gen_pipeline.database import AsyncSessionLocal as PatchedAsyncSessionLocal
    lead_data_valid = {
        "company_name": "Tech Corp",
        "website": "https://techcorp.com",
        "scraped_from_url": "https://techcorp.com/about",
        "canonical_url": "https://techcorp.com/canonical-about",
        "description": "A leading tech company.",
        "phone_numbers": ["+1-800-555-0001", "1-800-555-0002"],
        "emails": ["contact@techcorp.com", "sales@techcorp.com"],
        "addresses": ["1 Tech Plaza, Silicon Valley, CA"],
        "social_media_links": {"linkedin": "linkedin.com/company/techcorp"}
    }

    saved_lead_model = await save_lead(lead_data_valid)
    assert saved_lead_model is not None
    assert saved_lead_model.id is not None
    assert saved_lead_model.company_name == "Tech Corp"
    assert saved_lead_model.website == "https://techcorp.com"
    assert saved_lead_model.scraped_from_url == "https://techcorp.com/about"
    assert saved_lead_model.canonical_url == "https://techcorp.com/canonical-about"
    assert saved_lead_model.description == "A leading tech company."
    assert saved_lead_model.phone_numbers == ["+1-800-555-0001", "1-800-555-0002"]
    assert saved_lead_model.emails == ["contact@techcorp.com", "sales@techcorp.com"]
    assert saved_lead_model.addresses == ["1 Tech Plaza, Silicon Valley, CA"]
    assert saved_lead_model.social_media_links == {"linkedin": "linkedin.com/company/techcorp"}
    assert saved_lead_model.created_at is not None
    assert saved_lead_model.updated_at is not None


    async with PatchedAsyncSessionLocal() as session:
        retrieved_lead = await session.get(Lead, saved_lead_model.id)
        assert retrieved_lead is not None
        assert retrieved_lead.company_name == "Tech Corp"

@pytest.mark.asyncio
async def test_save_lead_minimal_data():
    """Test saving a lead with only the mandatory and some optional fields."""
    from lead_gen_pipeline.database import AsyncSessionLocal as PatchedAsyncSessionLocal
    lead_data_minimal = {
        "scraped_from_url": "https://minimalist.co/page",
        "website": "https://minimalist.co",
        "phone_numbers": [],
        "emails": [],
    }
    saved_lead_model = await save_lead(lead_data_minimal)
    assert saved_lead_model is not None
    assert saved_lead_model.id is not None
    assert saved_lead_model.scraped_from_url == "https://minimalist.co/page"
    assert saved_lead_model.website == "https://minimalist.co"
    assert saved_lead_model.company_name is None
    assert saved_lead_model.phone_numbers == []
    assert saved_lead_model.emails == []
    assert saved_lead_model.social_media_links is None

@pytest.mark.asyncio
async def test_save_lead_with_existing_session():
    """Test saving a lead when an existing db_session is provided."""
    from lead_gen_pipeline.database import AsyncSessionLocal as PatchedAsyncSessionLocal
    lead_data = {
        "company_name": "Session Corp",
        "website": "https://sessioncorp.com",
        "scraped_from_url": "https://sessioncorp.com/home",
    }
    async with PatchedAsyncSessionLocal() as session:
        saved_lead_model = await save_lead(lead_data, db_session=session)
        await session.commit() 

        assert saved_lead_model is not None
        assert saved_lead_model.id is not None
        assert saved_lead_model.company_name == "Session Corp"

        retrieved_lead = await session.get(Lead, saved_lead_model.id)
        assert retrieved_lead is not None
        assert retrieved_lead.company_name == "Session Corp"

    async with PatchedAsyncSessionLocal() as new_session: 
        retrieved_again = await new_session.get(Lead, saved_lead_model.id) # type: ignore
        assert retrieved_again is not None
        assert retrieved_again.company_name == "Session Corp"


@pytest.mark.asyncio
async def test_save_lead_handles_database_error_gracefully(monkeypatch):
    """Test that save_lead handles exceptions during commit and returns None."""
    lead_data_problematic = {
        "company_name": "Error Corp",
        "website": "https://errorcorp.com",
        "scraped_from_url": "https://errorcorp.com/page"
    }

    # This is the mocked session instance that will be returned by our factory
    mocked_session_instance = AsyncMock(spec=AsyncSession)
    
    # .commit() is an async method, its mock should raise an exception
    mocked_session_instance.commit = AsyncMock(side_effect=Exception("Simulated database commit error"))
    
    # .add() is a synchronous method on AsyncSession
    mocked_session_instance.add = MagicMock(return_value=None) 
    
    # .rollback() is an async method, its mock should be awaitable (AsyncMock default behavior)
    # We don't need to explicitly set .rollback here if default AsyncMock is fine.
    # If we wanted to assert it's called, it will be an AsyncMock by default.
    # mocked_session_instance.rollback = AsyncMock(return_value=None) # This would be if we wanted to control its return

    # .flush() and .refresh() are async and might be called.
    # Let them be default AsyncMocks.
    # mocked_session_instance.flush = AsyncMock()
    # mocked_session_instance.refresh = AsyncMock()


    def mock_async_session_local_factory(*args, **kwargs):
        class MockSessionContextManager:
            async def __aenter__(self):
                return mocked_session_instance
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        return MockSessionContextManager()

    monkeypatch.setattr("lead_gen_pipeline.database.AsyncSessionLocal", mock_async_session_local_factory)
    
    saved_lead_model = await save_lead(lead_data_problematic)
    
    assert saved_lead_model is None 
    mocked_session_instance.add.assert_called_once() 
    mocked_session_instance.commit.assert_called_once() 
    
    # rollback is an async method on AsyncSession, so its mock (attribute of AsyncMock)
    # should be an AsyncMock and assert_awaited_once should be used if we want to check it.
    # For now, we'll check if it was called, as the primary check is the commit failure and rollback logic.
    mocked_session_instance.rollback.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
