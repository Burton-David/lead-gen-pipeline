"""Tests that the generic/placeholder blocklists filter noise as intended."""

import pytest

from lead_gen_pipeline import generic_filters as gf
from lead_gen_pipeline.scraper import HTMLScraper


@pytest.fixture
def scraper():
    return HTMLScraper("<html></html>", "http://example.com")


@pytest.mark.parametrize(
    "phone, is_generic",
    [
        ("555-555-5555", True),
        ("(123) 456-7890", True),
        ("800-555-0100", True),
        ("000-000-0000", True),
        ("303-556-0123", False),
        ("555-0100", True),  # reserved fictional number
    ],
)
def test_generic_phone_detection(scraper, phone, is_generic):
    assert scraper._is_generic_phone(phone) is is_generic


@pytest.mark.parametrize(
    "email, is_generic",
    [
        ("info@example.com", True),
        ("test@example.com", True),
        ("name@domain.com", True),
        ("someone@anything.test", True),  # placeholder TLD
        ("real.person@acmecorp.com", False),
    ],
)
def test_generic_email_detection(scraper, email, is_generic):
    assert scraper._is_generic_email(email) is is_generic


def test_blocklists_are_nonempty_sets():
    for name in (
        "GENERIC_PHONE_PATTERNS",
        "GENERIC_EMAIL_PATTERNS",
        "GENERIC_EMAIL_DOMAINS",
        "GENERIC_COMPANY_TERMS",
        "PLACEHOLDER_WEBSITE_DOMAINS",
        "PLACEHOLDER_TLDS",
    ):
        value = getattr(gf, name)
        assert isinstance(value, set)
        assert value, f"{name} should not be empty"


def test_iana_reserved_domains_present():
    assert "example.com" in gf.PLACEHOLDER_WEBSITE_DOMAINS
    assert ".test" in gf.PLACEHOLDER_TLDS
