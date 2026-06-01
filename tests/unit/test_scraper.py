"""Tests for HTMLScraper extraction (company, phone, email, address, social).

Fixtures use realistic, non-placeholder data; cases that exercise the noise filter use
reserved/example values on purpose.
"""

import pytest

from lead_gen_pipeline.scraper import HTMLScraper

RICH_HTML = """
<html><head>
<title>Acme Robotics Inc. | Industrial Automation</title>
<meta property="og:site_name" content="Acme Robotics">
<meta name="description" content="Industrial automation solutions for factories.">
<link rel="canonical" href="https://acmerobotics.com/canonical">
</head><body>
<p>Email: <a href="mailto:sales@acmerobotics.com">sales@acmerobotics.com</a></p>
<p>Support: support@acmerobotics.com</p>
<p>Call: <a href="tel:+13035560123">(303) 556-0123</a></p>
<div itemscope itemtype="http://schema.org/PostalAddress">
  <span itemprop="streetAddress">500 Industrial Way</span>,
  <span itemprop="addressLocality">Denver</span>,
  <span itemprop="addressRegion">CO</span>
  <span itemprop="postalCode">80202</span>
</div>
<a href="https://linkedin.com/company/acme-robotics">LinkedIn</a>
<a href="https://twitter.com/acmerobotics">Twitter</a>
<a href="https://www.linkedin.com/login">login</a>
</body></html>
"""


def test_init_handles_empty_html():
    scraper = HTMLScraper("", "http://x.com")
    assert scraper.source_url == "http://x.com"
    assert str(scraper.soup) == ""


@pytest.mark.parametrize(
    "html, expected",
    [
        ('<meta property="og:site_name" content="Acme Robotics">', "Acme Robotics"),
        ("<title>Specific Product | Acme Robotics</title>", "Acme Robotics"),
        (
            '<div itemtype="http://schema.org/Organization">'
            '<span itemprop="name">Acme Robotics</span></div>',
            "Acme Robotics",
        ),
        ("<footer>© 2024 Acme Robotics Inc.</footer>", "Acme Robotics"),
        ("<title>Home</title>", None),  # generic page title filtered
        ("<p>no markers</p>", None),
    ],
)
def test_extract_company_name(html, expected):
    assert HTMLScraper(html, "http://x.com").extract_company_name() == expected


@pytest.mark.parametrize(
    "html, expected",
    [
        ("<a href='tel:+13035560123'>(303) 556-0123</a>", ["+13035560123"]),
        ("<p>Call 303-556-0123 or 303-556-0124</p>", ["+13035560123", "+13035560124"]),
        ("<p>Order: <a href='tel:18003569377'>1-800-FLOWERS</a></p>", ["+18003569377"]),
        ("<p>555-555-5555</p>", []),  # generic, filtered
        ("<p>123-456-7890</p>", []),  # generic, filtered
        ("<p>No numbers here.</p>", []),
    ],
)
def test_extract_phone_numbers(html, expected):
    scraper = HTMLScraper(html, "http://x.com")
    assert scraper.extract_phone_numbers() == sorted(expected)


@pytest.mark.parametrize(
    "html, expected",
    [
        ("<a href='mailto:sales@acme.co'>mail</a>", ["sales@acme.co"]),
        ("<p>Reach sales (at) acme (dot) co today</p>", ["sales@acme.co"]),
        ("<p>Contact: ops AT acme DOT co</p>", ["ops@acme.co"]),
        ("<p>a@acme.co and A@ACME.CO</p>", ["a@acme.co"]),  # dedup, case-fold
        ("<p>info@example.com</p>", []),  # generic domain, filtered
        ("<p>no emails</p>", []),
    ],
)
def test_extract_emails(html, expected):
    assert HTMLScraper(html, "http://x.com").extract_emails() == sorted(expected)


def test_cloudflare_email_decode_roundtrip():
    scraper = HTMLScraper("<html></html>", "http://x.com")
    email = "person@acmerobotics.com"
    key = 0x1A
    encoded = f"{key:02x}" + "".join(f"{ord(c) ^ key:02x}" for c in email)
    decoded = scraper._decode_cloudflare_email(f"/cdn-cgi/l/email-protection#{encoded}")
    assert decoded == email


@pytest.mark.parametrize(
    "html, region, needle",
    [
        (
            '<div itemscope itemtype="http://schema.org/PostalAddress">'
            '<span itemprop="streetAddress">500 Industrial Way</span>'
            '<span itemprop="addressLocality">Denver</span>'
            '<span itemprop="addressRegion">CO</span>'
            '<span itemprop="postalCode">80202</span></div>',
            "US",
            "500 Industrial Way",
        ),
        (
            "<address>1600 Pennsylvania Ave, Washington, DC 20500</address>",
            "US",
            "1600 Pennsylvania Ave",
        ),
    ],
)
def test_extract_addresses(html, region, needle):
    scraper = HTMLScraper(html, "http://x.com")
    scraper.default_region = region
    assert any(needle in addr for addr in scraper.extract_addresses())


@pytest.mark.parametrize(
    "html, expected",
    [
        (
            '<a href="https://linkedin.com/company/acme">in</a>'
            '<a href="https://twitter.com/acme">tw</a>',
            {
                "linkedin": "https://linkedin.com/company/acme",
                "twitter": "https://twitter.com/acme",
            },
        ),
        ('<a href="https://www.linkedin.com/login">login</a>', {}),  # excluded path
        (
            '<a href="www.twitter.com/acmehandle">no scheme</a>',
            {"twitter": "http://www.twitter.com/acmehandle"},
        ),
    ],
)
def test_extract_social_media_links(html, expected):
    assert HTMLScraper(html, "http://x.com").extract_social_media_links() == expected


@pytest.mark.parametrize(
    "html, expected",
    [
        (
            '<meta name="description" content="A real description here.">',
            "A real description here.",
        ),
        (
            '<meta property="og:description" content="OG description text.">',
            "OG description text.",
        ),
        ("<p>no meta description</p>", None),
    ],
)
def test_extract_description(html, expected):
    assert HTMLScraper(html, "http://x.com").extract_description() == expected


@pytest.mark.parametrize(
    "html, source, expected",
    [
        (
            '<link rel="canonical" href="https://acme.co/page">',
            "http://acme.co/x",
            "https://acme.co/page",
        ),
        (
            '<link rel="canonical" href="/relative">',
            "http://acme.co/x/",
            "http://acme.co/relative",
        ),
        ("<p>none</p>", "http://acme.co", None),
    ],
)
def test_extract_canonical_url(html, source, expected):
    assert HTMLScraper(html, source).extract_canonical_url() == expected


def test_scrape_holistic():
    data = HTMLScraper(RICH_HTML, "http://acmerobotics.com/contact").scrape()
    assert data["company_name"] == "Acme Robotics"
    assert data["website"] == "http://acmerobotics.com"
    assert data["scraped_from_url"] == "http://acmerobotics.com/contact"
    assert data["canonical_url"] == "https://acmerobotics.com/canonical"
    assert "Industrial automation" in data["description"]
    assert "+13035560123" in data["phone_numbers"]
    assert sorted(data["emails"]) == [
        "sales@acmerobotics.com",
        "support@acmerobotics.com",
    ]
    assert any("500 Industrial Way" in a for a in data["addresses"])
    assert data["social_media_links"] == {
        "linkedin": "https://linkedin.com/company/acme-robotics",
        "twitter": "https://twitter.com/acmerobotics",
    }
