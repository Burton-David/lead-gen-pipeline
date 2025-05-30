# tests/unit/test_scraper.py
# Version: Enhanced for Production Quality Testing (v12_updates)

import pytest
from pathlib import Path
import sys

PROJECT_ROOT_FOR_IMPORTS = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORTS))

from lead_gen_pipeline.scraper import HTMLScraper

# --- Test HTML Samples ---

SAMPLE_HTML_BASIC_CONTACT = """
<html>
<head><title>Basic Contact</title></head>
<body>
    <p>Contact us at <a href="mailto:info@mycompany.com">info@mycompany.com</a>.</p>
    <p>Phone: <a href="tel:123-456-7890">123-456-7890</a>.</p>
    <address>
        123 Business Rd, Suite 100, Businesstown, TX 75001
    </address>
    <a href="https://linkedin.com/company/mycompany">LinkedIn</a>
    <a href="https://twitter.com/mycompanyhandle">Twitter</a>
</body>
</html>
"""

SAMPLE_HTML_NO_INFO = """
<html>
<head><title>No Info</title></head>
<body>
    <p>This page has no specific contact information to extract.</p>
    <meta name="description" content="A very basic page.">
</body>
</html>
"""

SAMPLE_HTML_COMPLEX_FOOTER_AND_BODY = """
<html>
<head>
    <title>Complex Page Ltd.</title>
    <meta property="og:site_name" content="Complex Page Ltd">
    <meta name="description" content="This is a complex page with data in multiple places.">
    <link rel="canonical" href="https://www.complexdata.co/complex-page">
</head>
<body>
    <h1>Welcome to Complex Page Ltd.</h1>
    <section class="contact-details">
        <p>Email: <a href="mailto:support@complexdata.co">support@complexdata.co</a></p>
        <p>Phone: <span>+1-888-COMPLEX</span> (that's <a href="tel:18882667539">1-888-266-7539</a>)</p>
        <div itemprop itemscope itemtype="http://schema.org/Organization">
            <span itemprop="name">Complex Data Corp</span>
            <div itemprop="address" itemscope itemtype="http://schema.org/PostalAddress">
                <span itemprop="streetAddress">789 Tech Park Avenue, Suite 500</span>
                <span itemprop="addressLocality">Innovate City</span>,
                <span itemprop="addressRegion">CA</span>
                <span itemprop="postalCode">94043</span>
                <span itemprop="addressCountry">USA</span>.
            </div>
        </div>
    </section>
    <footer>
        <p>© Complex Page Ltd. All rights reserved.</p>
        <p>Reach out to sales: <a href="mailto:sales.department@complexdata.co">sales.department@complexdata.co</a></p>
        <p>Call our main line: 556-789-0123.</p>
        <address>Main Address: 456 Complex Ave, Footer City, ST 90000, USA.</address>
        <a href="https://www.youtube.com/user/ComplexDataChannel">YouTube</a>
        <a href="https://linkedin.com/company/complex-data-company">LinkedIn</a>
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
        <p>UK Office: <a href="tel:+442079460123">+44 (0) 20 7946 0123</a></p>
        <p>Vanity Line: 1-888-555-DATA</p>
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
        <a href="https://www.youtube.com/testbiz">YouTube</a>
    </div>
    <footer>
        General Address: Main Street 1, Big City, BC 12345. Phone: (555) 555-5555 ext. 123
    </footer>
</body>
</html>
"""

HTML_DEEP_NESTING_AND_WEIRD_SPACING = """
<div>
    <p>Call <span>now: <b>1</b > - <em>800</em></span><span>-<span>TOLL</span><span>FREE</span></span> !</p>
    <p>Email:<span>info</span>@<span>example.com</span></p>
</div>
"""

HTML_FOR_ADDRESS_EDGE_CASES = """
<html><body>
    <address>
        123 Main St<br>Anytown, CA, 90210
    </address>
    <div>
        PO Box 123, Anytown, CA 90210
    </div>
    <p>Our office: Fourth Street, Unit 5, Big City, New State 12345, CountryLand</p>
    <p>Somewhere Else, Non US City, ZZ 99999, Abroad</p>
    <div itemscope itemtype="http://schema.org/PostalAddress">
        <span itemprop="streetAddress">789 Test Parkway</span>
        <span itemprop="addressLocality">Testville</span>
        <span itemprop="postalCode">12345</span>
        <span itemprop="addressCountry">US</span>
    </div>
    <p>1 First St Anytown CA 12345</p> <p>Address: <span><span><span>10 Downing Street</span></span></span>, <span>London</span>, SW1A 2AA, <span>UK</span></p>
</body></html>
"""

HTML_FOR_SOCIAL_MEDIA_EDGE_CASES = """
<html><body>
    <a href="https://www.linkedin.com/company/test-co/about/">LinkedIn About Page</a>
    <a href="https://www.linkedin.com/in/john-doe-12345/detail/recent-activity/shares/">LinkedIn Activity</a>
    <a href="https://twitter.com/user/status/12345">Twitter Status</a>
    <a href="https://twitter.com/intent/tweet?text=hello">Twitter Intent</a>
    <a href="youtu.be/ID">YouTube Shortened</a>
    <a href="https://facebook.com/profile.php?id=1234567890">Facebook Profile PHP</a>
    <a href="https://facebook.com/SomePageName/photos_stream?ref=page_internal">Facebook Photos Stream</a>
    <a href="https://www.instagram.com/username/?hl=en">Instagram with lang param</a>
    <a href="http://x.com/share?url=http://example.com">X.com Share Link</a>
    <a href="https://www.tiktok.com/@username/video/12345?is_from_webapp=1&sender_device=pc">TikTok Video Link</a>
    <a href="https://www.pinterest.com/user_name/_saved/">Pinterest Saved Pins</a>
    <a href="https://www.linkedin.com/login">LinkedIn Login (exclusion)</a>
    <a href="www.twitter.com/anotheruser">Twitter without scheme</a>
    <a href="//facebook.com/schemelessfb">Schemeless Facebook</a>
    <a href="youtube.com/c/ComplexSolutionsVideo">Another Youtube Link</a>
</body></html>
"""

# --- Fixtures ---
@pytest.fixture
def basic_contact_scraper():
    return HTMLScraper(SAMPLE_HTML_BASIC_CONTACT, "http://mycompany.com")

@pytest.fixture
def no_info_scraper():
    return HTMLScraper(SAMPLE_HTML_NO_INFO, "http://noinfo.com")

@pytest.fixture
def complex_data_scraper():
    return HTMLScraper(SAMPLE_HTML_COMPLEX_FOOTER_AND_BODY, "http://complexdata.co")

@pytest.fixture
def mock_b2b_scraper():
    return HTMLScraper(MOCK_B2B_HTML_CONTENT_FOR_UNIT_TEST, "http://mock-b2b-site.com/contact")

@pytest.fixture
def deep_nesting_scraper():
    return HTMLScraper(HTML_DEEP_NESTING_AND_WEIRD_SPACING, "http://weirdhtml.com")

@pytest.fixture
def address_edge_case_scraper():
    scraper = HTMLScraper(HTML_FOR_ADDRESS_EDGE_CASES, "http://address-test.com")
    scraper.default_region = "US" 
    return scraper

@pytest.fixture
def social_media_edge_case_scraper():
    return HTMLScraper(HTML_FOR_SOCIAL_MEDIA_EDGE_CASES, "http://social-edge.com")


# --- Initialization and Basic Structure Tests ---
def test_scraper_initialization():
    scraper = HTMLScraper("<html></html>", "http://example.com")
    assert scraper.source_url == "http://example.com"
    assert scraper.soup is not None

def test_scraper_initialization_with_empty_html():
    scraper = HTMLScraper("", "http://example.com")
    assert scraper.source_url == "http://example.com"
    assert scraper.soup is not None
    assert str(scraper.soup) == ""


# --- Company Name Extraction Tests ---
@pytest.mark.parametrize("html_input, source_url, expected_name, description", [
    (SAMPLE_HTML_BASIC_CONTACT, "http://mycompany.com", None, "Basic contact, no clear company name markers"), 
    (SAMPLE_HTML_COMPLEX_FOOTER_AND_BODY, "http://complexdata.co", "Complex Page Ltd", "Complex HTML with og:site_name"),
    (MOCK_B2B_HTML_CONTENT_FOR_UNIT_TEST, "http://mock-b2b-site.com/contact", "TestBiz Solutions Official", "Mock B2B with og:site_name"),
    (SAMPLE_HTML_NO_INFO, "http://noinfo.com", None, "No info page, no company name"),
    ("<title>My Awesome Company</title>", "http://example.com", "My Awesome Company", "Title tag only"),
    ("<meta property=\"og:site_name\" content=\"OG Site Name Corp\">", "http://example.com", "OG Site Name Corp", "og:site_name only"),
    ("<meta property=\"og:title\" content=\"Specific Product | BrandName\">", "http://example.com", "BrandName", "og:title with separator"),
    ("<div itemtype=\"http://schema.org/Organization\"><span itemprop=\"name\">Schema Org Name</span></div>", "http://example.com", "Schema Org Name", "Schema.org Organization name"),
    ("<footer>© 2024 Copyright Holder Inc.</footer>", "http://example.com", "Copyright Holder Inc.", "Copyright in footer"),
    ("<h1>Main Title Co</h1>", "http://example.com", "Main Title Co", "H1 title (if spaCy used or simple heuristic)"),
])
def test_extract_company_name_various(html_input, source_url, expected_name, description):
    scraper = HTMLScraper(html_input, source_url)
    assert scraper.extract_company_name() == expected_name, description


# --- _extract_text_content() Specific Tests (Critical for Foundation) ---
@pytest.mark.parametrize("html_input, element_selector, expected_text, description", [
    ("<div>Hello <script>ignore this</script> World</div>", "div", "Hello World", "Script content ignored"),
    ("<p>Text with <br> new line.</p>", "p", "Text with new line.", "BR tag handled as space"),
    ("<p>Text with<span>nested</span> tags and <span>more</span>.</p>", "p", "Text with nested tags and more.", "Nested tags combined"),
    ("<p> leading and trailing spaces </p>", "p", "leading and trailing spaces", "Leading/trailing spaces handled by clean_text"),
    ("<div>Multiple  spaces   here.</div>", "div", "Multiple spaces here.", "Multiple spaces collapsed"),
    ("<div>Unicode: café and résumé</div>", "div", "Unicode: café and résumé", "Basic Unicode preserved"),
    ("<div>Text with non-breaking space.</div>", "div", "Text with non-breaking space.", "NBSP handled as space"),
    ("<div><span>Part1</span><span>Part2</span></div>", "div", "Part1 Part2", "Adjacent inline elements get space"),
    ("<div>Line1<br/>Line2<br />Line3</div>", "div", "Line1 Line2 Line3", "Multiple BRs"),
    ("<div>Hyphen-test: ‑ – — − ‒ ― ‐</div>", "div", "Hyphen-test: -------", "Various hyphens normalized to single hyphen"),
    ("<p>Text witha comment removed.</p>", "p", "Text witha comment removed.", "HTML comments removed"), 
    (HTML_DEEP_NESTING_AND_WEIRD_SPACING, "div > p:first-of-type", "Call now: 1-800-TOLL FREE !", "Deeply nested spans - get_text with space separator then hyphen norm"),
    (HTML_DEEP_NESTING_AND_WEIRD_SPACING, "div > p:nth-of-type(2)", "Email: info@example.com", "Email split in spans - get_text with space separator and email norm"),
    ("<div><style>.foo{color:red}</style>Hidden style text</div>", "div", "Hidden style text", "Style tag content ignored"),
    ("<div>Content <ul><li>Item 1</li> <li>Item 2</li></ul> Post-list</div>", "div", "Content Item 1 Item 2 Post-list", "List item text extraction"),
    ("<p>Text&More Text</p>", "p", "Text&More Text", "HTML entities decoded"), 
])
def test_extract_text_content_detailed(html_input, element_selector, expected_text, description):
    scraper = HTMLScraper(html_input, "http://testing.com")
    element = scraper.soup.select_one(element_selector)
    assert scraper._extract_text_content(element) == expected_text, description


# --- Phone Number Extraction Tests ---
@pytest.mark.parametrize("html_snippet, region, expected_e164_phones, description", [
    ("<p>Call us at <a href='tel:18005551212'>1-800-555-1212</a></p>", "US", ["+18005551212"], "Simple tel link, text matches href"),
    ("<p><a href='tel:+18005551212'>Call <b>+1 (800) 555-1212</b> Now</a></p>", "US", ["+18005551212"], "Tel link, formatted text preferred"),
    ("<p>Phone: 888.556.0100</p>", "US", ["+18885560100"], "Plain text with dots (non-555)"),
    ("<div>Contact: (303) 556-0101 or 303-556-0102</div>", "US", sorted(["+13035560101", "+13035560102"]), "Multiple in one div (non-555)"),
    ("<p>Tel. +44 20 7946 0958</p>", "GB", ["+442079460958"], "International format (GB) in text"),
    ("<p>Tel. 020 7946 0958</p>", "GB", ["+442079460958"], "National GB format in text"), 
    ("<a href='tel:+49-30-1234567'>Call Germany</a>", "DE", ["+49301234567"], "International DE in tel:href"),
    ("<span>Main: 1-800-GOOD-BOY and 556-123-4567</span>", "US", sorted(["+18004663269", "+15561234567"]), "Mixed vanity (GOODBOY) and numeric (non-555)"),
    ("<p>Ext: 1234. Our number is 1-800-TEST-EXT ext. 1234</p>", "US", ["+18008378398"], "Number with extension"),
    ("<p>Our fax: 1-800-FAX-MEEE</p>", "US", ["+18003296333"], "Fax number as vanity"),
    ("<p>Tel: <a href='tel:1-800-POPCORN'>1-800-POPCORN</a></p>", "US", ["+18007672676"], "Vanity number in tel link"),
    ("<p>Call 1.800.GET.THIS</p>", "US", ["+18004388447"], "Vanity number in text with dots"),
    ("<div><a href='tel:1-800-CONTACT'><span>1-800-CONTACT</span></a></div>", "US", ["+18002668228"], "Tel link with vanity text in span"),
    ("Phone: <span>1-800</span>-<span>FLOWERS</span>", "US", ["+18003569377"], "Vanity number split across spans"),
    ("Call <a href='tel:18002222222'>1-800-AAA-AAAA</a> and <a href='tel:18002222222'>1 (800) AAA-AAAA</a>", "US", ["+18002222222"], "Deduplicate same vanity number"),
    ("<p>Order ID: 1234567890, Phone: 987-654-3210</p>", "US", ["+19876543210"], "Avoid non-phone numbers"),
    ("<a href='tel:5561112222'></a><p>Text: 556-111-2222</p>", "US", ["+15561112222"], "Tel link empty text (non-555)"),
    ("<a href='tel:ignoreme'>Call 556-222-3333</a>", "US", ["+15562223333"], "Tel link invalid href, get from text (non-555)"),
    ("<p>Call <a href='tel:+12345678900'>raw number in href</a>, or try <a><span>+1 (234) 567-8900</span></a> (no href)</p>", "US", ["+12345678900"], "Tel href E.164, also in text"),
    ("<p>Do not call: 12345 or 9876543210123456</p>", "US", [], "Numbers too short/long"),
    ("<p>No numbers here.</p>", "US", [], "No phone numbers at all"),
    ("<p>Call 5561234567 or 556.123.4567</p>", "US", ["+15561234567"], "No separators and dot separators (non-555)"),
    ("<p>Number is 556-456-7890. Also 556.456.7890. And (556) 456 7890.</p>", "US", ["+15564567890"], "Multiple formats (non-555)"),
    (SAMPLE_HTML_NO_INFO, "US", [], "No phone numbers in no_info sample"),
    ("Call us at 1800.INVALID.NUM", "US", [], "Vanity with too many letters between numbers"),
    ("Phone: 123-456-78901", "US", [], "Too many digits in last part"),
    ("Contact +1 800 CALL NOW PLEASE", "US", ["+18002255669"], "Trailing words after vanity"),
    ("Tel: +1 (555) 555 5555 ext. 123, also +1.555.555.5555 x123", "US", ["+15555555555"], "Numbers with extensions, deduplicate"),
    (HTML_DEEP_NESTING_AND_WEIRD_SPACING, "US", ["+18008655373"], "Deeply nested phone (1-800-TOLLFREE)"),
])
def test_extract_phone_numbers_overview(html_snippet, region, expected_e164_phones, description):
    scraper = HTMLScraper(html_snippet, "http://example.com")
    scraper.default_region = region
    phones = scraper.extract_phone_numbers()
    assert sorted(phones) == sorted(expected_e164_phones), f"Test failed for: {description}. Got {sorted(phones)}"


# --- Email Extraction Tests ---
@pytest.mark.parametrize("html_input, expected_emails, description", [
    (SAMPLE_HTML_BASIC_CONTACT, sorted(["info@mycompany.com"]), "Basic mailto links"), 
    (SAMPLE_HTML_COMPLEX_FOOTER_AND_BODY, sorted(["sales.department@complexdata.co", "support@complexdata.co"]), "Complex HTML emails"),
    ("<p>Email: test@example.com. Also TEST@EXAMPLE.COM.</p>", ["test@example.com"], "Plain text email, deduplication"),
    ("No emails here.", [], "No emails present"),
    (SAMPLE_HTML_NO_INFO, [], "No emails in no_info sample"),
    (MOCK_B2B_HTML_CONTENT_FOR_UNIT_TEST, sorted(["info@testbizsolutions.com", "sales@testbizsolutions.com"]), "Mock B2B emails"),
    ("<p>info [at] example [dot] com</p>", ["info@example.com"], "Obfuscated with [at] [dot]"),
    ("Contact us: user(at)domain(dot)co(dot)uk", ["user@domain.co.uk"], "Obfuscated with (at) (dot)"),
    ("<a href='/cdn-cgi/l/email-protection#dabcb3bfb49abfa2bba9b2b3f4b9b5b7'>[email protected]</a> by Cloudflare", ["user@example.com"], "Cloudflare encoded email"), 
    (HTML_DEEP_NESTING_AND_WEIRD_SPACING, ["info@example.com"], "Email split in spans"),
    ("<p>Email us at <img src='email.png'> (image email)</p>", [], "Email as image (should not be extracted)"),
    ("<p>Contact: no-reply AT example DOT com</p>", ["no-reply@example.com"], "Obfuscated with AT DOT (uppercase)"),
])
def test_extract_emails_various(html_input, expected_emails, description, monkeypatch):
    scraper = HTMLScraper(html_input, "http://testing.com")
    if "Cloudflare encoded email" in description:
        def mock_decode_cf(encoded_str):
            if encoded_str == "/cdn-cgi/l/email-protection#dabcb3bfb49abfa2bba9b2b3f4b9b5b7" or encoded_str == "dabcb3bfb49abfa2bba9b2b3f4b9b5b7":
                return "user@example.com" 
            return None
        monkeypatch.setattr(scraper, '_decode_cloudflare_email', mock_decode_cf)

    assert sorted(scraper.extract_emails()) == sorted(expected_emails), description


# --- Address Extraction Tests ---
@pytest.mark.parametrize("html_input, region, expected_addresses_subset, description", [
    ("""<div itemscope itemtype="http://schema.org/PostalAddress">
          <span itemprop="streetAddress">123 Main St</span>,
          <span itemprop="addressLocality">Anytown</span>, <span itemprop="addressRegion">CA</span>
          <span itemprop="postalCode">90210</span></div>""",
     "US", ["123 Main St, Anytown, CA 90210"], "Schema.org PostalAddress basic"),
    (HTML_FOR_ADDRESS_EDGE_CASES, "US", [
        "123 Main St, Anytown, CA, 90210",
        "PO Box 123, Anytown, CA 90210",
        "Fourth Street, Unit 5, Big City, New State 12345, CountryLand",
        "789 Test Parkway, Testville, 12345", 
        "1 First St, Anytown, CA 12345",
        "10 Downing Street, London, SW1A 2AA, UK"
        ], "Various address formats including schema and plain text"),
    (SAMPLE_HTML_BASIC_CONTACT, "US", ["123 Business Rd, Suite 100, Businesstown, TX 75001"], "Basic contact page address div"),
    (MOCK_B2B_HTML_CONTENT_FOR_UNIT_TEST, "US",
     ["123 Innovation Drive, Tech City, TS 90210", 
      "456 Business Ave, Metroville, ST 10001", 
      "Main Street 1, Big City, BC 12345" 
      ], "Mock B2B schema and footer addresses"),
    (SAMPLE_HTML_COMPLEX_FOOTER_AND_BODY, "US",
     ["789 Tech Park Avenue, Suite 500, Innovate City, CA 94043", 
      "456 Complex Ave, Footer City, ST 90000"], 
      "Complex HTML schema and footer addresses"),
    (SAMPLE_HTML_NO_INFO, "US", [], "No addresses in no_info sample"),
    ("<div>123 Fake St Anytown AK 99501 USA</div>", "US", ["123 Fake St, Anytown, AK 99501"], "US address no commas, USA removed by formatter"),
    ("<div>Some random text then <span>Hauptstrasse 10, 10115 Berlin, Germany</span> and more.</div>", "DE", ["Hauptstrasse 10, 10115 Berlin, Germany"], "German address embedded"),
    ("<p>Office: <span>1 Rue de la Paix</span><span>Paris</span><span>France</span> <span>75002</span></p>", "FR", ["1 Rue de la Paix, Paris, 75002, France"], "Address split across multiple spans"),
])
def test_extract_addresses_various(html_input, region, expected_addresses_subset, description):
    scraper = HTMLScraper(html_input, "http://testing.com")
    scraper.default_region = region
    extracted_addresses = scraper.extract_addresses()
    
    missing_addresses = []
    for expected_addr_pattern in expected_addresses_subset:
        if not any(expected_addr_pattern.lower() in extracted_addr.lower() for extracted_addr in extracted_addresses):
            missing_addresses.append(expected_addr_pattern)
    
    assert not missing_addresses, \
        f"Test failed for: {description}. Expected address patterns not found: {missing_addresses}. Extracted: {extracted_addresses}"
    
    if not expected_addresses_subset: 
        assert not extracted_addresses, f"Test failed for: {description}. Expected empty list but got {extracted_addresses}"


# --- Social Media Links Extraction Tests ---
@pytest.mark.parametrize("html_input, source_url, expected_social_links, description", [
    (SAMPLE_HTML_BASIC_CONTACT, "https://www.mycompany.com/page",
     {"linkedin": "https://linkedin.com/company/mycompany", "twitter": "https://twitter.com/mycompanyhandle"},
     "Basic social links"),
    (MOCK_B2B_HTML_CONTENT_FOR_UNIT_TEST, "http://mock-b2b-site.com/contact",
     {"linkedin": "https://linkedin.com/company/testbiz", "twitter": "http://twitter.com/testbizinc",
      "facebook": "https://www.facebook.com/TestBizSolutions", "youtube": "https://www.youtube.com/testbiz"},
     "Mock B2B social links"),
    (SAMPLE_HTML_COMPLEX_FOOTER_AND_BODY, "http://complexdata.co",
     {"youtube": "https://www.youtube.com/user/ComplexDataChannel", "linkedin": "https://linkedin.com/company/complex-data-company"},
     "Complex HTML social links"),
    (SAMPLE_HTML_NO_INFO, "http://noinfo.com", {}, "No social links in no_info sample"),
    (HTML_FOR_SOCIAL_MEDIA_EDGE_CASES, "http://social-edge.com", {
        "linkedin": "https://www.linkedin.com/company/test-co/about/", 
        "twitter": "http://www.twitter.com/anotheruser", 
        "youtube": "youtu.be/ID", 
        "facebook": "https://facebook.com/profile.php?id=1234567890", 
        "instagram": "https://www.instagram.com/username/?hl=en",
        "tiktok": "https://www.tiktok.com/@username/video/12345?is_from_webapp=1&sender_device=pc", 
        "pinterest": "https://www.pinterest.com/user_name/_saved/", 
    }, "Social media edge cases"),
    ("""<a href="//facebook.com/schemelessfb">Schemeless</a>""", "http://example.com",
     {"facebook": "http://facebook.com/schemelessfb"}, "Schemeless Facebook URL"),
    ("""<a href="www.twitter.com/noschemeuser">No Scheme Twitter</a>""", "http://example.com",
     {"twitter": "http://www.twitter.com/noschemeuser"}, "No scheme Twitter URL"),
])
def test_extract_social_media_links_various(html_input, source_url, expected_social_links, description):
    scraper = HTMLScraper(html_input, source_url)
    extracted = scraper.extract_social_media_links()
    assert extracted == expected_social_links, f"Test failed for: {description}. Got {extracted}"


# --- Description Extraction Tests ---
@pytest.mark.parametrize("html_input, expected_description, description", [
    (SAMPLE_HTML_BASIC_CONTACT, None, "Basic contact, no meta description"), 
    (SAMPLE_HTML_COMPLEX_FOOTER_AND_BODY, "This is a complex page with data in multiple places.", "Complex HTML meta description"),
    (MOCK_B2B_HTML_CONTENT_FOR_UNIT_TEST, "TestBiz offers cutting-edge solutions for B2B needs. Contact us for more info.", "Mock B2B meta description"),
    (SAMPLE_HTML_NO_INFO, "A very basic page.", "No info page meta description"),
    ("<meta name=\"description\" content=\"Test description here.\">", "Test description here.", "Simple name=description"),
    ("<meta property=\"og:description\" content=\"OG description here.\">", "OG description here.", "og:description"),
    ("<meta name=\"twitter:description\" content=\"Twitter description here.\">", "Twitter description here.", "twitter:description"),
    ("", None, "Empty HTML, no description"),
])
def test_extract_description_various(html_input, expected_description, description):
    scraper = HTMLScraper(html_input, "http://testing.com")
    assert scraper.extract_description() == expected_description, description

# --- Canonical URL Extraction Tests ---
@pytest.mark.parametrize("html_input, source_url, expected_canonical, description", [
    (SAMPLE_HTML_BASIC_CONTACT, "http://mycompany.com/page1", None, "Basic contact, no canonical"), 
    (SAMPLE_HTML_COMPLEX_FOOTER_AND_BODY, "http://complexdata.co/somepath", "https://www.complexdata.co/complex-page", "Complex HTML canonical"),
    (MOCK_B2B_HTML_CONTENT_FOR_UNIT_TEST, "http://mock-b2b-site.com/contact", "http://mock-b2b-site.com/canonical-contact", "Mock B2B canonical"),
    (SAMPLE_HTML_NO_INFO, "http://noinfo.com", None, "No info page, no canonical"),
    ("<link rel=\"canonical\" href=\"https://example.com/canonical-page\">", "http://example.com/test", "https://example.com/canonical-page", "Absolute canonical URL"),
    ("<link rel=\"canonical\" href=\"/relative-canonical\">", "http://example.com/test/", "http://example.com/relative-canonical", "Relative canonical URL"),
    ("", "http://example.com", None, "Empty HTML, no canonical"),
])
def test_extract_canonical_url_various(html_input, source_url, expected_canonical, description):
    scraper = HTMLScraper(html_input, source_url)
    assert scraper.extract_canonical_url() == expected_canonical, description


# --- Holistic Scrape Method Tests ---
def test_scrape_holistic_mock_b2b_updated_expectations(mock_b2b_scraper: HTMLScraper):
    data = mock_b2b_scraper.scrape()
    mock_b2b_scraper.default_region = "US"

    assert data["company_name"] == "TestBiz Solutions Official"
    assert data["website"] == "http://mock-b2b-site.com"
    assert data["scraped_from_url"] == "http://mock-b2b-site.com/contact"
    assert data["canonical_url"] == "http://mock-b2b-site.com/canonical-contact"
    assert "TestBiz offers cutting-edge solutions" in (data["description"] or "")

    expected_phones = sorted([
        "+155501234567", 
        "+155501237654", 
        "+442079460123",
        "+18885553282",  
        "+15555555555"   
    ])
    actual_phones = sorted([p for p in data["phone_numbers"] if p])
    assert actual_phones == expected_phones, f"Phone numbers mismatch. Expected {expected_phones}, Got {actual_phones}"

    expected_emails = sorted(["info@testbizsolutions.com", "sales@testbizsolutions.com"])
    assert sorted(data["emails"]) == expected_emails

    found_addresses = data["addresses"]
    assert any("123 Innovation Drive" in addr and "Tech City" in addr for addr in found_addresses), "Schema address missing/incorrect"
    assert any("456 Business Ave" in addr and "Metroville" in addr for addr in found_addresses), "Plain text office address missing/incorrect"
    assert any("Main Street 1" in addr and "Big City" in addr for addr in found_addresses), "Footer address missing/incorrect"

    expected_social_links = {
        "linkedin": "https://linkedin.com/company/testbiz",
        "twitter": "http://twitter.com/testbizinc",
        "facebook": "https://www.facebook.com/TestBizSolutions",
        "youtube": "https://www.youtube.com/testbiz"
    }
    assert data["social_media_links"] == expected_social_links

def test_scrape_holistic_complex_data(complex_data_scraper: HTMLScraper):
    data = complex_data_scraper.scrape()
    complex_data_scraper.default_region = "US" 

    assert data["company_name"] == "Complex Page Ltd" 
    assert data["website"] == "https://www.complexdata.co"
    assert data["scraped_from_url"] == "http://complexdata.co" 
    assert data["canonical_url"] == "https://www.complexdata.co/complex-page"
    assert data["description"] == "This is a complex page with data in multiple places."

    expected_phones = sorted([
        "+18882667539", 
        "+15567890123"  
    ])
    actual_phones = sorted([p for p in data["phone_numbers"] if p])
    assert actual_phones == expected_phones, f"Phone numbers mismatch. Expected {expected_phones}, Got {actual_phones}"

    expected_emails = sorted(["support@complexdata.co", "sales.department@complexdata.co"])
    assert sorted(data["emails"]) == expected_emails

    found_addresses = data["addresses"]
    assert any("789 Tech Park Avenue" in addr and "Innovate City" in addr for addr in found_addresses)
    assert any("456 Complex Ave" in addr and "Footer City" in addr for addr in found_addresses)

    expected_social_links = {
        "youtube": "https://www.youtube.com/user/ComplexDataChannel",
        "linkedin": "https://linkedin.com/company/complex-data-company"
    }
    assert data["social_media_links"] == expected_social_links

def test_scrape_holistic_no_info(no_info_scraper: HTMLScraper):
    data = no_info_scraper.scrape()
    assert data["company_name"] is None 
    assert data["website"] == "http://noinfo.com" 
    assert data["scraped_from_url"] == "http://noinfo.com"
    assert data["canonical_url"] is None
    assert data["description"] == "A very basic page."
    assert data["phone_numbers"] == []
    assert data["emails"] == []
    assert data["addresses"] == []
    assert data["social_media_links"] == {}


if __name__ == '__main__':
    pytest.main([__file__, "-vv"])
