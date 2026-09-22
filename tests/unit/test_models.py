"""Tests for the Lead ORM model."""

from datetime import datetime

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from lead_gen_pipeline.models import Base, Lead


@pytest.fixture
def sync_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def test_lead_creation_and_defaults(sync_session):
    lead = Lead(
        company_name="Test Company",
        website="http://testcompany.com",
        scraped_from_url="http://testcompany.com/source",
        phone_numbers=["+18005551212"],
        emails=["test@testcompany.com"],
        addresses=["123 Main St, Testville"],
        social_media_links={"linkedin": "http://linkedin.com/company/test"},
        industry_tags=["Technology"],
    )
    sync_session.add(lead)
    sync_session.commit()
    sync_session.refresh(lead)

    assert lead.id is not None
    assert lead.company_name == "Test Company"
    assert isinstance(lead.created_at, datetime)
    assert isinstance(lead.updated_at, datetime)

    # JSON-backed fields round-trip.
    assert lead.phone_numbers == ["+18005551212"]
    assert lead.industry_tags == ["Technology"]
    assert lead.social_media_links == {"linkedin": "http://linkedin.com/company/test"}

    # Convenience accessors.
    assert lead.phone_numbers_list == ["+18005551212"]
    assert lead.emails_list == ["test@testcompany.com"]
    assert lead.addresses_list == ["123 Main St, Testville"]
    assert lead.social_media_dict == {"linkedin": "http://linkedin.com/company/test"}


def test_lead_nullable_fields(sync_session):
    lead = Lead(scraped_from_url="http://minimal.com")
    sync_session.add(lead)
    sync_session.commit()
    sync_session.refresh(lead)

    assert lead.company_name is None
    assert lead.phone_numbers is None
    assert lead.phone_numbers_list is None
    assert lead.social_media_dict is None


def test_lead_repr():
    lead = Lead(id=1, company_name="Repro Corp", website="http://repro.co")
    assert (
        repr(lead)
        == "<Lead(id=1, company_name='Repro Corp', website='http://repro.co')>"
    )


def test_table_has_all_columns():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    columns = {c["name"] for c in inspect(engine).get_columns("leads")}
    expected = {
        "id",
        "company_name",
        "website",
        "scraped_from_url",
        "canonical_url",
        "description",
        "phone_numbers",
        "emails",
        "addresses",
        "social_media_links",
        "industry_tags",
        "chamber_name",
        "chamber_url",
        "created_at",
        "updated_at",
    }
    assert columns == expected
    Base.metadata.drop_all(engine)
