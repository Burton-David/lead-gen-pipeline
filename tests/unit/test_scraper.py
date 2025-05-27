# tests/unit/test_scraper.py
# Version: Gemini-2025-05-26 22:45 EDT

import pytest
from pathlib import Path
import sys

PROJECT_ROOT_FOR_IMPORTS = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORTS))

from lead_gen_pipeline.scraper import HTMLScraper

# --- Test HTML Samples ---

SAMPLE_HTML_BASIC_CONTACT = """
<html>
    <head>
        <title>Basic Contact Page - MyCompany</title>
        <meta name="description" content="Contact MyCompany for services.">
        <meta property="og:site_name" content="MyCo Official">
        <link rel="canonical" href="https://www.mycompany.com/contact-us">
    </head>
    <body>
        <h1>Contact Us</h1>
        <p>Email us at <a href="mailto:contact@mycompany.com">contact@mycompany.com</a>.</p>
        <p>Or call us on: <a href="tel:+1-555-123-4567">+1 (555) 123-4567</a>.</p>
        <p>General Inquiries: <a href="mailto:info@mycompany.com?subject=Inquiry">info@mycompany.com</a></p>
        <div class="address">
            MyCompany Ltd.<br>
            123 Business Rd, Suite 100<br>
            Businesstown, TX 75001
        </div>
        <div class="social-links">
            <a href="https://linkedin.com/company/mycompany">LinkedIn</a>
            <a href="https://twitter.com/mycompanyhandle">Twitter Profile</a>
        </div>
        <footer>
            Our main office line: (555) 987-6543.
        </footer>
    </body>
</html>
"""

SAMPLE_HTML_NO_INFO = """
<html>
    <head><title>Empty Page</title></head>
    <body><p>Nothing to see here.</p></body>
</html>
"""

SAMPLE_HTML_COMPLEX_FOOTER = """
<html>
    <head><title>Complex Footer Co</title></head>
    <body>
        <p>Main content</p>
        <footer>
            <div>
                <span>Contact:</span>
                <span><a href="tel:123-456-7890">Call Us: 123-456-7890</a></span> |
                <span>Email: <a href="mailto:support@complex.com">support@complex.com</a></span>
            </div>
            <p>&copy; Complex Footer Co. All rights reserved. |
                <a href="https://linkedin.com/company/complexfooter">LinkedIn</a> |
                Address: 456 Complex Ave, Footer City, ST 90000
            </p>
        </footer>
    </body>
</html>
"""

MOCK_B2B_HTML_CONTENT_FOR_UNIT_TEST = """
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
        General Address: Main Street 1, Big City, BC 12345. Phone: 1-888-555-DATA.
        Useless number sequence: 12345 67890 123 456.
        Another: <b>(555) 555-5555 ext. 123</b>
    </footer>
</body>
</html>
"""


# --- Fixtures ---

@pytest.fixture
def basic_contact_scraper():
    return HTMLScraper(html_content=SAMPLE_HTML_BASIC_CONTACT, source_url="https://www.mycompany.com/somepage")

@pytest.fixture
def no_info_scraper():
    return HTMLScraper(html_content=SAMPLE_HTML_NO_INFO, source_url="https://www.noinfo.com")

@pytest.fixture
def complex_footer_scraper():
    return HTMLScraper(html_content=SAMPLE_HTML_COMPLEX_FOOTER, source_url="https://www.complex.com")

@pytest.fixture
def mock_b2b_scraper():
    return HTMLScraper(html_content=MOCK_B2B_HTML_CONTENT_FOR_UNIT_TEST, source_url="http://mock-b2b-site.com/contact")


# --- Initial Tests ---

def test_scraper_initialization(basic_contact_scraper: HTMLScraper, no_info_scraper: HTMLScraper):
    assert basic_contact_scraper.soup is not None
    assert basic_contact_scraper.source_url == "https://www.mycompany.com/somepage"
    assert no_info_scraper.soup is not None

def test_scraper_initialization_with_empty_html():
    scraper = HTMLScraper(html_content="", source_url="https://www.empty.com")
    assert scraper.soup is not None
    assert str(scraper.soup) == ""
    data = scraper.scrape()
    assert data["company_name"] is None

# --- Company Name Extraction Tests ---
def test_extract_company_name_og_site_name(basic_contact_scraper: HTMLScraper):
    name = basic_contact_scraper.extract_company_name()
    assert name == "MyCo Official"

def test_extract_company_name_title_fallback():
    html = "<title>Title Company Name | Services</title>"
    scraper = HTMLScraper(html, "http://example.com")
    assert scraper.extract_company_name() == "Title Company Name"

def test_extract_company_name_no_info(no_info_scraper: HTMLScraper):
    assert no_info_scraper.extract_company_name() is None

def test_extract_company_name_mock_b2b(mock_b2b_scraper: HTMLScraper):
    name = mock_b2b_scraper.extract_company_name()
    assert name == "TestBiz Solutions Official"


# --- Phone Number Extraction Tests ---
def test_extract_phone_numbers_basic(basic_contact_scraper: HTMLScraper):
    phones = basic_contact_scraper.extract_phone_numbers()
    expected_phones = sorted(["+1 (555) 123-4567", "(555) 987-6543"])
    assert phones == expected_phones

def test_extract_phone_numbers_complex_footer(complex_footer_scraper: HTMLScraper):
    phones = complex_footer_scraper.extract_phone_numbers()
    assert phones == ["123-456-7890"]

def test_extract_phone_numbers_no_info(no_info_scraper: HTMLScraper):
    assert no_info_scraper.extract_phone_numbers() == []

def test_extract_phone_numbers_mock_b2b(mock_b2b_scraper: HTMLScraper):
    phones = mock_b2b_scraper.extract_phone_numbers()
    expected_phones = sorted([
        "+1 (555) 0123-4567",
        "555-0123-7654",
        "1-888-555-DATA",
        "(555) 555-5555 ext. 123"
    ])
    assert phones == expected_phones

@pytest.mark.parametrize("html_snippet, expected_phones_list, description", [
    ("<p>Call us at <a href='tel:18005551212'>1-800-555-1212</a></p>", ["1-800-555-1212"], "Simple tel link, text matches href"),
    ("<p><a href='tel:+18005551212'>Call <b>+1 (800) 555-1212</b> Now</a></p>", ["+1 (800) 555-1212"], "Tel link, formatted text preferred"),
    ("<p>Phone: 888.555.0100</p>", ["888.555.0100"], "Plain text with dots"),
    ("<div>Contact: (303) 555-0101 or 303-555-0102</div>", sorted(["(303) 555-0101", "303-555-0102"]), "Multiple in one div"),
    ("<p>Tel. +44 20 7946 0958</p>", ["+44 20 7946 0958"], "International format"),
    ("<span>Main: 1-555-GOOD-BOY and 555-123-4567</span>", sorted(["1-555-GOOD-BOY", "555-123-4567"]), "Mixed vanity and numeric"),
    ("<p>Call 5551234567 or 555.123.4567</p>", sorted(["555.123.4567", "5551234567"]), "No separators and dot separators"),
    ("<p>Ext: 1234. Our number is 1-800-TEST-EXT ext. 1234</p>", ["1-800-TEST-EXT ext. 1234"], "Number with extension"),
    ("<p>Order ID: 1234567890, Phone: 987-654-3210</p>", ["987-654-3210"], "Avoid non-phone numbers"),
    ("<a href='tel:5551112222'></a><p>Text: 555-111-2222</p>", ["555-111-2222"], "Tel link empty text, text version preferred due to formatting"),
    ("<a href='tel:ignoreme'>Call 555-222-3333</a>", ["555-222-3333"], "Tel link invalid href (not plausible), get from text"),
    ("<p>Call <a href='tel:+12345678900'>raw number in href</a>, or try <a><span>+1 (234) 567-8900</span></a> (no href)</p>", sorted(["+1 (234) 567-8900", "+12345678900"]), "Tel href and text in span are different numbers"),
    ("<p>Phone: +12345678900, +1 234 567 8900, 1 (234) 567-8900</p>", sorted(["+1 234 567 8900", "+12345678900", "1 (234) 567-8900"]), "Various international formats in text"),
    ("<p>Number is 555-456-7890. Also 555.456.7890. And (555) 456 7890.</p>", sorted(["(555) 456 7890", "555-456-7890", "555.456.7890"]), "Multiple formats, deduplicated"),
    ("<p>Do not call: 12345 or 9876543210123456 (too long/short for plausible)</p>", [], "Numbers too short or too long"),
    ("<p>Our fax: 1-800-FAX-MEEE</p>", ["1-800-FAX-MEEE"], "Fax number (alphanumeric regex will catch it)"),
    ("<p>Tel: <a href='tel:1-555-POPCORN'>1-555-POPCORN</a></p>", ["1-555-POPCORN"], "Vanity number in tel link"),
    ("<p>Call 1.800.GET.THIS</p>", ["1.800.GET.THIS"], "Vanity number in text"),
    ("<div><a href='tel:1-800-CONTACT'><span>1-800-CONTACT</span></a></div>", ["1-800-CONTACT"], "Tel link with text in span"),
    ("Phone: <span>1-800</span>-<span>LETTERS</span>", ["1-800-LETTERS"], "Number split across spans"),
    ("Call <a href='tel:18002223333'>1-800-AAA-BBBB</a> and <a href='tel:18002223333'>1 (800) AAA-BBBB</a>", ["1 (800) AAA-BBBB"], "Deduplicate different formats of same vanity number, prefer more complete"),
])
def test_extract_phone_numbers_various_snippets(html_snippet, expected_phones_list, description):
    scraper = HTMLScraper(html_snippet, "http://example.com")
    phones = scraper.extract_phone_numbers()
    assert phones == sorted(expected_phones_list), f"Test failed for: {description}"


# --- Email Extraction Tests ---
def test_extract_emails_basic(basic_contact_scraper: HTMLScraper):
    emails = basic_contact_scraper.extract_emails()
    expected_emails = sorted(["contact@mycompany.com", "info@mycompany.com"])
    assert emails == expected_emails

def test_extract_emails_complex_footer(complex_footer_scraper: HTMLScraper):
    emails = complex_footer_scraper.extract_emails()
    assert emails == ["support@complex.com"]

def test_extract_emails_no_info(no_info_scraper: HTMLScraper):
    assert no_info_scraper.extract_emails() == []

def test_extract_emails_mock_b2b(mock_b2b_scraper: HTMLScraper):
    emails = mock_b2b_scraper.extract_emails()
    expected_emails = sorted(["info@testbizsolutions.com", "sales@testbizsolutions.com"])
    assert emails == expected_emails


# --- Address Extraction Tests ---
def test_extract_addresses_basic_schema(basic_contact_scraper: HTMLScraper):
    html_with_schema_address = """
    <html><body>
        <div itemprop itemtype="http://schema.org/PostalAddress">
            <span itemprop="streetAddress">123 Main St</span>,
            <span itemprop="addressLocality">Anytown</span>,
            <span itemprop="addressRegion">CA</span>
        </div>
    </body></html>
    """
    scraper = HTMLScraper(html_with_schema_address, "http://schema.com")
    addresses = scraper.extract_addresses()
    assert addresses == ["123 Main St, Anytown, CA"]

def test_extract_addresses_mock_b2b(mock_b2b_scraper: HTMLScraper):
    addresses = mock_b2b_scraper.extract_addresses()
    assert "123 Innovation Drive, Tech City, TS, 90210" in addresses
    assert "General Address: Main Street 1, Big City, BC 12345. Phone: 1-888-555-DATA." in addresses

def test_extract_addresses_no_info(no_info_scraper: HTMLScraper):
    assert no_info_scraper.extract_addresses() == []

# --- Social Media Links Extraction Tests ---
def test_extract_social_media_links_basic(basic_contact_scraper: HTMLScraper):
    social_links = basic_contact_scraper.extract_social_media_links()
    assert social_links.get("linkedin") == "https://linkedin.com/company/mycompany"
    assert social_links.get("twitter") == "https://twitter.com/mycompanyhandle"
    assert len(social_links) == 2

def test_extract_social_media_links_complex_footer(complex_footer_scraper: HTMLScraper):
    social_links = complex_footer_scraper.extract_social_media_links()
    assert social_links.get("linkedin") == "https://linkedin.com/company/complexfooter"
    assert len(social_links) == 1

def test_extract_social_media_links_no_info(no_info_scraper: HTMLScraper):
    assert no_info_scraper.extract_social_media_links() == {}

def test_extract_social_media_links_mock_b2b(mock_b2b_scraper: HTMLScraper):
    social_links = mock_b2b_scraper.extract_social_media_links()
    assert social_links.get("linkedin") == "https://linkedin.com/company/testbiz"
    assert social_links.get("twitter") == "http://twitter.com/testbizinc"
    assert social_links.get("facebook") == "https://www.facebook.com/TestBizSolutions"
    assert len(social_links) == 3


# --- Description Extraction Tests ---
def test_extract_description_basic(basic_contact_scraper: HTMLScraper):
    description = basic_contact_scraper.extract_description()
    assert description == "Contact MyCompany for services."

def test_extract_description_no_info(no_info_scraper: HTMLScraper):
    assert no_info_scraper.extract_description() is None

def test_extract_description_mock_b2b(mock_b2b_scraper: HTMLScraper):
    description = mock_b2b_scraper.extract_description()
    assert description == "TestBiz offers cutting-edge solutions for B2B needs. Contact us for more info."


# --- Canonical URL Extraction Tests ---
def test_extract_canonical_url_basic(basic_contact_scraper: HTMLScraper):
    canonical = basic_contact_scraper.extract_canonical_url()
    assert canonical == "https://www.mycompany.com/contact-us"

def test_extract_canonical_url_no_info(no_info_scraper: HTMLScraper):
    assert no_info_scraper.extract_canonical_url() is None

def test_extract_canonical_url_mock_b2b(mock_b2b_scraper: HTMLScraper):
    canonical = mock_b2b_scraper.extract_canonical_url()
    assert canonical == "http://mock-b2b-site.com/canonical-contact"


# --- Full Scrape Method Tests ---
def test_scrape_method_basic(basic_contact_scraper: HTMLScraper):
    data = basic_contact_scraper.scrape()
    assert data["company_name"] == "MyCo Official"
    assert "contact@mycompany.com" in data["emails"]
    assert "+1 (555) 123-4567" in data["phone_numbers"]
    assert data["website"] == "https://www.mycompany.com"
    assert data["scraped_from_url"] == "https://www.mycompany.com/somepage"
    assert data["social_media_links"].get("linkedin") is not None

def test_scrape_method_no_info(no_info_scraper: HTMLScraper):
    data = no_info_scraper.scrape()
    assert data["company_name"] is None
    assert data["emails"] == []
    assert data["phone_numbers"] == []
    assert data["website"] == "https://www.noinfo.com"
    assert data["social_media_links"] == {}
    assert data["description"] is None
    assert data["canonical_url"] is None

def test_scrape_method_mock_b2b(mock_b2b_scraper: HTMLScraper):
    data = mock_b2b_scraper.scrape()
    assert data["company_name"] == "TestBiz Solutions Official"
    assert "info@testbizsolutions.com" in data["emails"]
    
    expected_phones = sorted([
        "+1 (555) 0123-4567", "555-0123-7654", "1-888-555-DATA", "(555) 555-5555 ext. 123"
    ])
    assert sorted(data["phone_numbers"]) == expected_phones

    assert data["website"] == "http://mock-b2b-site.com"
    assert data["scraped_from_url"] == "http://mock-b2b-site.com/contact"
    assert data["social_media_links"].get("linkedin") is not None
    assert data["description"] == "TestBiz offers cutting-edge solutions for B2B needs. Contact us for more info."
    assert data["canonical_url"] == "http://mock-b2b-site.com/canonical-contact"


if __name__ == '__main__':
    pytest.main([__file__, "-vv"])
