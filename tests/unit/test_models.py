# tests/unit/test_models.py
# Version: Gemini-2025-05-26 18:21 UTC

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import sys
from pathlib import Path

PROJECT_ROOT_FOR_IMPORTS = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORTS))

from lead_gen_pipeline.models import Base, Lead

# Use a synchronous SQLite in-memory database for model structure testing
SYNC_DB_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def sync_db_session():
    engine = create_engine(SYNC_DB_URL)
    Base.metadata.create_all(engine) # Create tables
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine) # Drop tables

def test_lead_model_creation_and_defaults(sync_db_session):
    """Test basic Lead model instantiation and default values."""
    new_lead = Lead(
        company_name="Test Company",
        website="http://testcompany.com",
        scraped_from_url="http://testcompany.com/source",
        phone_numbers=["123-456-7890"],
        emails=["test@testcompany.com"],
        addresses=["123 Main St, Testville"],
        social_media_links={"linkedin": "http://linkedin.com/testcompany"}
    )
    sync_db_session.add(new_lead)
    sync_db_session.commit()
    sync_db_session.refresh(new_lead)

    assert new_lead.id is not None
    assert new_lead.company_name == "Test Company"
    assert new_lead.website == "http://testcompany.com"
    assert new_lead.scraped_from_url == "http://testcompany.com/source"
    assert new_lead.created_at is not None
    assert isinstance(new_lead.created_at, datetime)
    assert new_lead.updated_at is not None
    assert isinstance(new_lead.updated_at, datetime)

    # Test JSON fields
    assert new_lead.phone_numbers == ["123-456-7890"]
    assert new_lead.emails == ["test@testcompany.com"]
    assert new_lead.addresses == ["123 Main St, Testville"]
    assert new_lead.social_media_links == {"linkedin": "http://linkedin.com/testcompany"}

    # Test convenience properties
    assert new_lead.phone_numbers_list == ["123-456-7890"]
    assert new_lead.emails_list == ["test@testcompany.com"]
    assert new_lead.addresses_list == ["123 Main St, Testville"]
    assert new_lead.social_media_dict == {"linkedin": "http://linkedin.com/testcompany"}


def test_lead_model_nullable_fields(sync_db_session):
    """Test that nullable fields can indeed be null."""
    minimal_lead = Lead(scraped_from_url="http://minimal.com")
    sync_db_session.add(minimal_lead)
    sync_db_session.commit()
    sync_db_session.refresh(minimal_lead)

    assert minimal_lead.id is not None
    assert minimal_lead.company_name is None
    assert minimal_lead.website is None
    assert minimal_lead.canonical_url is None
    assert minimal_lead.description is None
    assert minimal_lead.phone_numbers is None
    assert minimal_lead.emails is None
    assert minimal_lead.addresses is None
    assert minimal_lead.social_media_links is None

    assert minimal_lead.phone_numbers_list is None
    assert minimal_lead.emails_list is None
    assert minimal_lead.addresses_list is None
    assert minimal_lead.social_media_dict is None


def test_lead_model_repr(sync_db_session):
    """Test the __repr__ method of the Lead model."""
    lead = Lead(id=1, company_name="Repro Corp", website="http://repro.co")
    # Note: We are not adding to session here, just testing __repr__
    assert repr(lead) == "<Lead(id=1, company_name='Repro Corp', website='http://repro.co')>"
    lead_no_id = Lead(company_name="No ID Corp", website="http://noid.co")
    assert repr(lead_no_id) == "<Lead(id=None, company_name='No ID Corp', website='http://noid.co')>"


def test_lead_table_structure():
    """Inspect the table structure created by SQLAlchemy."""
    engine = create_engine(SYNC_DB_URL)
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = inspector.get_columns('leads')

    expected_columns = {
        "id": "INTEGER",
        "company_name": "VARCHAR",
        "website": "VARCHAR",
        "scraped_from_url": "VARCHAR",
        "canonical_url": "VARCHAR",
        "description": "TEXT",
        "phone_numbers": "JSON", # SQLAlchemy JSON type maps to TEXT in SQLite if native JSON not supported by driver version
        "emails": "JSON",
        "addresses": "JSON",
        "social_media_links": "JSON",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    }

    for col in columns:
        assert col['name'] in expected_columns
        # Type affinity can be tricky with SQLite, so we check for common ones.
        # SQLAlchemy's JSON type often becomes TEXT in SQLite.
        col_type_str = str(col['type']).upper()
        expected_type_str = expected_columns[col['name']].upper()

        if expected_type_str == "JSON" and "TEXT" in col_type_str : # SQLite stores JSON as TEXT
             pass # This is acceptable for SQLite
        elif expected_type_str in col_type_str:
             pass
        else:
            assert False, f"Column {col['name']} type mismatch. Expected containing '{expected_type_str}', got '{col_type_str}'"


    # Clean up for this specific test if needed, though fixture handles it mostly
    Base.metadata.drop_all(engine)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])