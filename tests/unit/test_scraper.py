# tests/unit/test_scraper.py
# Version: Gemini-2025-05-27 T16:27:00Z (Revised for Comprehensive Overview)
"""
This test suite aims to provide a succinct yet comprehensive overview of the
HTMLScraper's capabilities in lead_gen_pipeline.scraper.py. It focuses on:
1.  Detailed testing of `extract_phone_numbers` to showcase the current performance
    and behavior of the integrated `phonenumbers` library across various input formats.
2.  Holistic testing of the main `scrape()` method using representative complex HTML
    to demonstrate the scraper's ability to extract all target data fields.
3.  Focused unit tests for individual extraction methods to verify their specific logic.

Reviewing these tests and their results should offer a clear picture of "where we are at"
with the scraper's data extraction quality.
"""

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
            International: +44 20 7123 4567
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

SAMPLE_HTML_COMPLEX_FOOTER_AND_BODY = """
<html>
    <head>
        <title>Complex Data Co. - Solutions & Services</title>
        <meta property="og:site_name" content="Complex Data Company (OG)">
        <meta name="description" content="Complex Data Co offers diverse solutions. Find our details.">
        <link rel="canonical" href="http://complexdata.co/main">
    </head>
    <body>
        <p>Reach out via <a href="mailto:sales.department@complexdata.co">sales.department@complexdata.co</a>.</p>
        <p>Phone (USA): 1-800-COMPLEX. Phone (UK): <a href="tel:+44-208-123-4567">+44 208 123 4567</a>.</p>
        <address itemprop itemtype="http://schema.org/PostalAddress">
            <strong itemprop="name">Complex Data Co. HQ</strong><br>
            <span itemprop="streetAddress">789 Tech Park Avenue, Suite 500</span><br>
            <span itemprop="addressLocality">Innovate City</span>,
            <span itemprop="addressRegion">CA</span>
            <span itemprop="postalCode">94043</span>
            <span itemprop="addressCountry">USA</span>
        </address>
        <p>Follow us on <a href="https://www.youtube.com/user/ComplexDataChannel">YouTube</a>.</p>
        <footer>
            <div>
                <span>Contact:</span>
                <span><a href="tel:123-456-7890">Support: 123-456-7890 (deprecated)</a></span> |
                <span>Email: <a href="mailto:support@complexdata.co">support@complexdata.co</a></span>
            </div>
            <p>© Complex Data Co. All rights reserved. |
                <a href="https://linkedin.com/company/complex-data-company">Our LinkedIn</a> |
                Main Address: 456 Complex Ave, Footer City, ST 90000, USA.
                </p>
            <p>General contact (German office): +49 30 12345678</p>
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
        <p>Support Line: 555-0123-7654 (Local)</p>
        <p>International Inquiries: +44 (0) 20 7946 0123</p>
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
        <a href="https://www.youtube.com/testbiz">YouTube Channel</a>
    </div>
    <footer>
        General Address: Main Street 1, Big City, BC 12345. Phone: 1-888-555-DATA.
        Useless number sequence: 12345 67890 123 456.
        Another valid one: <b>(555) 555-5555 ext. 123</b>
    </footer>
</body>
</html>
"""

# --- Fixtures ---

@pytest.fixture
def basic_contact_scraper():
    scraper = HTMLScraper(html_content=SAMPLE_HTML_BASIC_CONTACT, source_url="https://www.mycompany.com/somepage")
    scraper.default_region = "US" # Explicitly set for consistency in these tests
    return scraper

@pytest.fixture
def no_info_scraper():
    return HTMLScraper(html_content=SAMPLE_HTML_NO_INFO, source_url="https://www.noinfo.com")

@pytest.fixture
def complex_data_scraper():
    scraper = HTMLScraper(html_content=SAMPLE_HTML_COMPLEX_FOOTER_AND_BODY, source_url="http://complexdata.co/contact")
    # Default region will be US unless overridden in specific tests if needed for parsing ambiguity
    scraper.default_region = "US"
    return scraper

@pytest.fixture
def mock_b2b_scraper():
    scraper = HTMLScraper(html_content=MOCK_B2B_HTML_CONTENT_FOR_UNIT_TEST, source_url="http://mock-b2b-site.com/contact")
    scraper.default_region = "US"
    return scraper

# --- Helper for comparing lists of dicts or complex structures if needed ---
# (Not strictly necessary for current scraper output, but good practice)

# --- Initialization and Basic Structure Tests ---

def test_scraper_initialization(basic_contact_scraper: HTMLScraper, no_info_scraper: HTMLScraper):
    assert basic_contact_scraper.soup is not None
    assert basic_contact_scraper.source_url == "https://www.mycompany.com/somepage"
    assert no_info_scraper.soup is not None

def test_scraper_initialization_with_empty_html():
    scraper = HTMLScraper(html_content="", source_url="https://www.empty.com")
    assert scraper.soup is not None
    assert str(scraper.soup) == "" # Empty soup
    data = scraper.scrape() # Should not error
    assert data["company_name"] is None # Expect graceful handling

# --- Company Name Extraction Tests ---

@pytest.mark.parametrize("html_input, expected_name, description", [
    (SAMPLE_HTML_BASIC_CONTACT, "MyCo Official", "OG Site Name Present"),
    ("<title>Title Co. | Home</title><meta property='og:site_name' content=''>", "Title Co.", "Title Fallback when OG is empty"),
    ("<title>Generic Title Only</title>", "Generic Title Only", "Title only, not too generic by default rules"),
    ("<title>Home</title>", None, "Generic title 'Home' should be ignored"),
    (SAMPLE_HTML_NO_INFO, None, "No company name identifiable"),
    (MOCK_B2B_HTML_CONTENT_FOR_UNIT_TEST, "TestBiz Solutions Official", "Mock B2B from OG site name"),
    (SAMPLE_HTML_COMPLEX_FOOTER_AND_BODY, "Complex Data Company (OG)", "Complex HTML from OG site name"),
])
def test_extract_company_name_various(html_input, expected_name, description):
    scraper = HTMLScraper(html_input, "http://testing.com")
    assert scraper.extract_company_name() == expected_name, description

# --- Phone Number Extraction Tests ---

@pytest.mark.parametrize("html_snippet, region, expected_e164_phones, description", [
    # --- Start of test cases from the original test file ---
    # Basic US numbers
    ("<p>Call us at <a href='tel:18005551212'>1-800-555-1212</a></p>", "US", ["+18005551212"], "Simple tel link, text matches href"),
    ("<p><a href='tel:+18005551212'>Call <b>+1 (800) 555-1212</b> Now</a></p>", "US", ["+18005551212"], "Tel link, formatted text preferred (parsed from text)"),
    ("<p>Phone: 888.555.0100</p>", "US", ["+18885550100"], "Plain text with dots"),
    ("<div>Contact: (303) 555-0101 or 303-555-0102</div>", "US", sorted(["+13035550101", "+13035550102"]), "Multiple in one div"),

    # International
    ("<p>Tel. +44 20 7946 0958</p>", "GB", ["+442079460958"], "International format (GB) in text"),
    ("<p>Tel. 020 7946 0958</p>", "GB", ["+442079460958"], "National GB format in text"),
    ("<a href='tel:+49-30-1234567'>Call Germany</a>", "DE", ["+49301234567"], "International DE in tel:href"),

    # Vanity Numbers (phonenumbers library converts letters to digits)
    ("<span>Main: 1-800-GOOD-BOY and 555-123-4567</span>", "US", sorted(["+18004663269", "+15551234567"]), "Mixed vanity (GOODBOY) and numeric"),
    ("<p>Ext: 1234. Our number is 1-800-TEST-EXT ext. 1234</p>", "US", ["+18008378398"], "Number with extension (extension ignored by E.164)"),
    ("<p>Our fax: 1-800-FAX-MEEE</p>", "US", ["+18003296333"], "Fax number as vanity"),
    ("<p>Tel: <a href='tel:1-800-POPCORN'>1-800-POPCORN</a></p>", "US", ["+18007672676"], "Vanity number in tel link (text preferred)"),
    ("<p>Call 1.800.GET.THIS</p>", "US", ["+18004388447"], "Vanity number in text with dots"),
    ("<div><a href='tel:1-800-CONTACT'><span>1-800-CONTACT</span></a></div>", "US", ["+18002668228"], "Tel link with vanity text in span"),
    ("Phone: <span>1-800</span>-<span>FLOWERS</span>", "US", ["+18003569377"], "Vanity number split across spans"),
    ("Call <a href='tel:18002222222'>1-800-AAA-AAAA</a> and <a href='tel:18002222222'>1 (800) AAA-AAAA</a>", "US", ["+18002222222"], "Deduplicate different formats of same vanity number"),

    # Edge cases
    ("<p>Order ID: 1234567890, Phone: 987-654-3210</p>", "US", ["+19876543210"], "Avoid non-phone numbers (Order ID potentially ignored by matcher)"),
    ("<a href='tel:5551112222'></a><p>Text: 555-111-2222</p>", "US", ["+15551112222"], "Tel link empty text, gets from href; text is also same number"),
    ("<a href='tel:ignoreme'>Call 555-222-3333</a>", "US", ["+15552223333"], "Tel link invalid href, get from text"),
    # The following case depends on how _parse_and_format_phone handles parsing with None region if '+' is present.
    # If href_obj = phonenumbers.parse(phone_from_href_raw, None) works for '+12345678900'
    # and text_obj = phonenumbers.parse(link_text, self.default_region) also works.
    # The scraper logic tries to reconcile them. E.164 is the goal.
    ("<p>Call <a href='tel:+12345678900'>raw number in href</a>, or try <a><span>+1 (234) 567-8900</span></a> (no href)</p>", "US", ["+12345678900"], "Tel href is E.164, text is also E.164 format (deduplicated)"),
    ("<p>Do not call: 12345 or 9876543210123456 (too long/short for plausible)</p>", "US", [], "Numbers too short or too long to be valid"),
    ("<p>No numbers here.</p>", "US", [], "No phone numbers at all"),
    ("<p>Call 5551234567 or 555.123.4567</p>", "US", ["+15551234567"], "No separators and dot separators (deduplicated)"),
    ("<p>Number is 555-456-7890. Also 555.456.7890. And (555) 456 7890.</p>", "US", ["+15554567890"], "Multiple formats, deduplicated to E.164"),
    # --- End of original test cases, new ones can be added below ---
    (SAMPLE_HTML_NO_INFO, "US", [], "No phone numbers in no_info sample"),
])
def test_extract_phone_numbers_overview(html_snippet, region, expected_e164_phones, description):
    """
    Provides an overview of phone number extraction using the `phonenumbers` library.
    Tests various formats, including US, international, vanity, and edge cases.
    Expected output is a sorted list of unique numbers in E.164 format.
    This demonstrates the current capabilities and robustness of the phone parsing logic.
    """
    scraper = HTMLScraper(html_snippet, "http://example.com")
    scraper.default_region = region # Set region for the test case
    phones = scraper.extract_phone_numbers()
    assert phones == sorted(expected_e164_phones), f"Test failed for: {description}"

# --- Email Extraction Tests ---
@pytest.mark.parametrize("html_input, expected_emails, description", [
    (SAMPLE_HTML_BASIC_CONTACT, sorted(["contact@mycompany.com", "info@mycompany.com"]), "Basic mailto links"),
    (SAMPLE_HTML_COMPLEX_FOOTER_AND_BODY, sorted(["sales.department@complexdata.co", "support@complexdata.co"]), "Complex HTML emails"),
    ("<p>Email: test@example.com. Also TEST@EXAMPLE.COM.</p>", ["test@example.com"], "Plain text email, case-insensitivity and deduplication"),
    ("No emails here.", [], "No emails present"),
    (SAMPLE_HTML_NO_INFO, [], "No emails in no_info sample"),
    (MOCK_B2B_HTML_CONTENT_FOR_UNIT_TEST, sorted(["info@testbizsolutions.com", "sales@testbizsolutions.com"]), "Mock B2B emails"),
])
def test_extract_emails_various(html_input, expected_emails, description):
    scraper = HTMLScraper(html_input, "http://testing.com")
    assert scraper.extract_emails() == expected_emails, description


# --- Address Extraction Tests ---
# Address extraction is complex; these tests cover basic schema and some keyword heuristics.
# More comprehensive testing would require many varied real-world examples.
@pytest.mark.parametrize("html_input, expected_addresses_subset, description", [
    ("""<div itemprop itemtype="http://schema.org/PostalAddress">
          <span itemprop="streetAddress">123 Main St</span>,
          <span itemprop="addressLocality">Anytown</span>, CA
       </div>""",
     ["123 Main St, Anytown, CA"], "Schema.org PostalAddress basic"),
    (SAMPLE_HTML_BASIC_CONTACT, ["123 Business Rd, Suite 100, Businesstown, TX 75001"], "Basic contact page address div"),
    (MOCK_B2B_HTML_CONTENT_FOR_UNIT_TEST,
     ["123 Innovation Drive, Tech City, TS, 90210",
      "Our other office is at 456 Business Ave, Metroville, ST 10001.", # This is how the current scraper extracts it
      "General Address: Main Street 1, Big City, BC 12345. Phone: 1-888-555-DATA."],
     "Mock B2B schema and footer addresses"),
    (SAMPLE_HTML_COMPLEX_FOOTER_AND_BODY,
     ["789 Tech Park Avenue, Suite 500, Innovate City, CA, 94043, USA",
      "Main Address: 456 Complex Ave, Footer City, ST 90000, USA."],
      "Complex HTML schema and footer addresses"),
    (SAMPLE_HTML_NO_INFO, [], "No addresses in no_info sample"),
])
def test_extract_addresses_various(html_input, expected_addresses_subset, description):
    scraper = HTMLScraper(html_input, "http://testing.com")
    extracted_addresses = scraper.extract_addresses()
    # For subset checking, ensure all expected are found. Extracted might have more.
    for expected_addr in expected_addresses_subset:
        assert any(expected_addr in extracted_addr for extracted_addr in extracted_addresses), \
            f"Expected address '{expected_addr}' not found in {extracted_addresses} for: {description}"
    if not expected_addresses_subset: # If expecting empty, ensure it is.
        assert not extracted_addresses


# --- Social Media Links Extraction Tests ---
@pytest.mark.parametrize("html_input, expected_social_links, description", [
    (SAMPLE_HTML_BASIC_CONTACT,
     {"linkedin": "https://linkedin.com/company/mycompany", "twitter": "https://twitter.com/mycompanyhandle"},
     "Basic social links"),
    (MOCK_B2B_HTML_CONTENT_FOR_UNIT_TEST,
     {"linkedin": "https://linkedin.com/company/testbiz", "twitter": "http://twitter.com/testbizinc",
      "facebook": "https://www.facebook.com/TestBizSolutions", "youtube": "https://www.youtube.com/testbiz"},
     "Mock B2B social links"),
    (SAMPLE_HTML_COMPLEX_FOOTER_AND_BODY,
     {"youtube": "https://www.youtube.com/user/ComplexDataChannel", "linkedin": "https://linkedin.com/company/complex-data-company"},
     "Complex HTML social links"),
    (SAMPLE_HTML_NO_INFO, {}, "No social links in no_info sample"),
])
def test_extract_social_media_links_various(html_input, expected_social_links, description):
    scraper = HTMLScraper(html_input, "http://testing.com") # Base URL for relative link resolution
    assert scraper.extract_social_media_links() == expected_social_links, description

# --- Description Extraction Tests ---
# Add near other specific extraction tests

@pytest.mark.parametrize("html_input, element_selector, expected_text, description", [
    ("<div>Hello <script>ignore this</script> World</div>", "div", "Hello World", "Script content ignored"),
    ("<p>Text with <br> new line.</p>", "p", "Text with new line.", "BR tag handled as space"),
    ("<p>Text with<span>nested</span> tags and <span>more</span>.</p>", "p", "Text with nested tags and more.", "Nested tags combined"),
    ("<p> leading and trailing spaces </p>", "p", "leading and trailing spaces", "Leading/trailing spaces handled by clean_text"),
    ("<div>Multiple  spaces   here.</div>", "div", "Multiple spaces here.", "Multiple spaces collapsed"),
    ("<div>Unicode: café and résumé</div>", "div", "Unicode: café and résumé", "Basic Unicode preserved (further normalization tests if specific issues arise)"),
    ("<div>Text with non-breaking&nbsp;space.</div>", "div", "Text with non-breaking space.", "NBSP handled as space"),
    ("<div><span>Part1</span><span>Part2</span></div>", "div", "Part1 Part2", "Adjacent inline elements get space if _extract_text_content adds for block-like behavior or if spans are treated as such"),
    ("<div>Line1<br/>Line2<br />Line3</div>", "div", "Line1 Line2 Line3", "Multiple BRs"),
    ("<div>Hyphen-test: – — ‐</div>", "div", "Hyphen-test: - - -", "Various hyphens normalized (if _extract_text_content implements this)"),
    # Add more cases for comments, complex nesting, etc.
])
def test_extract_text_content_detailed(html_input, element_selector, expected_text, description):
    scraper = HTMLScraper(html_input, "http://testing.com")
    element = scraper.soup.select_one(element_selector)
    assert scraper._extract_text_content(element) == expected_text, description

# --- Canonical URL Extraction Tests ---
@pytest.mark.parametrize("html_input, base_url, expected_canonical_url, description", [
    (SAMPLE_HTML_BASIC_CONTACT, "https://www.mycompany.com/somepage", "https://www.mycompany.com/contact-us", "Basic canonical link"),
    (MOCK_B2B_HTML_CONTENT_FOR_UNIT_TEST, "http://mock-b2b-site.com/contact", "http://mock-b2b-site.com/canonical-contact", "Mock B2B canonical link"),
    (SAMPLE_HTML_COMPLEX_FOOTER_AND_BODY, "http://complexdata.co/contact", "http://complexdata.co/main", "Complex HTML canonical link"),
    ("""<html><head><link rel="canonical" href="/relative/path"></head></html>""", "http://example.com/base/", "http://example.com/relative/path", "Relative canonical link"),
    (SAMPLE_HTML_NO_INFO, "http://noinfo.com", None, "No canonical link in no_info sample"),
])
def test_extract_canonical_url_various(html_input, base_url, expected_canonical_url, description):
    scraper = HTMLScraper(html_input, base_url)
    assert scraper.extract_canonical_url() == expected_canonical_url, description

# --- Holistic Scrape Method Tests ---

def test_scrape_holistic_mock_b2b(mock_b2b_scraper: HTMLScraper):
    """
    Tests the main scrape() method on a comprehensive B2B mock HTML.
    This provides an overview of how all extractors perform together.
    """
    data = mock_b2b_scraper.scrape()

    assert data["company_name"] == "TestBiz Solutions Official"
    assert data["website"] == "http://mock-b2b-site.com" # Derived from canonical or source
    assert data["scraped_from_url"] == "http://mock-b2b-site.com/contact"
    assert data["canonical_url"] == "http://mock-b2b-site.com/canonical-contact"
    assert data["description"] == "TestBiz offers cutting-edge solutions for B2B needs. Contact us for more info."

    expected_phones = sorted([
        "+155501234567",  # from "+1 (555) 0123-4567"
        "+155501237654",  # from "555-0123-7654 (Local)"
        "+442079460123",  # from "+44 (0) 20 7946 0123"
        "+18885553282",   # from "1-888-555-DATA" (D=3, A=2, T=8)
        "+15555555555"    # from "(555) 555-5555 ext. 123"
    ])
    assert data["phone_numbers"] == expected_phones

    expected_emails = sorted(["info@testbizsolutions.com", "sales@testbizsolutions.com"])
    assert data["emails"] == expected_emails

    # Address extraction can be tricky; verify key addresses are present
    # The current scraper's address extraction might combine or split them in specific ways.
    # We check for presence of key parts or compare as sets if order/exact joining isn't guaranteed.
    found_addresses = data["addresses"]
    assert "123 Innovation Drive, Tech City, TS, 90210" in found_addresses
    assert "Our other office is at 456 Business Ave, Metroville, ST 10001." in found_addresses # As per current scraper logic
    assert "General Address: Main Street 1, Big City, BC 12345. Phone: 1-888-555-DATA." in found_addresses # As per current scraper logic

    expected_social_links = {
        "linkedin": "https://linkedin.com/company/testbiz",
        "twitter": "http://twitter.com/testbizinc",
        "facebook": "https://www.facebook.com/TestBizSolutions",
        "youtube": "https://www.youtube.com/testbiz"
    }
    assert data["social_media_links"] == expected_social_links

def test_scrape_holistic_complex_data(complex_data_scraper: HTMLScraper):
    """
    Tests the main scrape() method on the 'complex_data_scraper' HTML sample.
    """
    data = complex_data_scraper.scrape()
    complex_data_scraper.default_region = "US" # Ensure context for parsing

    assert data["company_name"] == "Complex Data Company (OG)"
    assert data["website"] == "http://complexdata.co" # from canonical
    assert data["scraped_from_url"] == "http://complexdata.co/contact"
    assert data["canonical_url"] == "http://complexdata.co/main"
    assert data["description"] == "Complex Data Co offers diverse solutions. Find our details."

    # Phones from complex_data_scraper:
    # "1-800-COMPLEX" (1-800-266-7539) -> +18002667539
    # "+44-208-123-4567" (tel link) -> +442081234567
    # "123-456-7890" (Support deprecated) -> +11234567890
    # "+49 30 12345678" (German office) -> +493012345678
    expected_phones = sorted([
        "+18002667539",
        "+442081234567",
        "+11234567890",
        "+493012345678"
    ])
    assert data["phone_numbers"] == expected_phones

    expected_emails = sorted(["sales.department@complexdata.co", "support@complexdata.co"])
    assert data["emails"] == expected_emails

    # Addresses from complex_data_scraper:
    # Schema: "789 Tech Park Avenue, Suite 500, Innovate City, CA, 94043, USA"
    # Footer: "Main Address: 456 Complex Ave, Footer City, ST 90000, USA."
    found_addresses = data["addresses"]
    assert "789 Tech Park Avenue, Suite 500, Innovate City, CA, 94043, USA" in found_addresses
    assert "Main Address: 456 Complex Ave, Footer City, ST 90000, USA." in found_addresses

    expected_social_links = {
        "youtube": "https://www.youtube.com/user/ComplexDataChannel",
        "linkedin": "https://linkedin.com/company/complex-data-company"
    }
    assert data["social_media_links"] == expected_social_links

def test_scrape_holistic_no_info(no_info_scraper: HTMLScraper):
    """
    Tests the main scrape() method on an HTML sample with no extractable info.
    Ensures graceful handling and appropriate empty/None values.
    """
    data = no_info_scraper.scrape()

    assert data["company_name"] is None
    assert data["website"] == "https://www.noinfo.com" # Derived from source_url
    assert data["scraped_from_url"] == "https://www.noinfo.com"
    assert data["canonical_url"] is None
    assert data["description"] is None
    assert data["phone_numbers"] == []
    assert data["emails"] == []
    assert data["addresses"] == []
    assert data["social_media_links"] == {}


if __name__ == '__main__':
    pytest.main([__file__, "-vv"])