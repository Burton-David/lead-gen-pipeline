#!/usr/bin/env python3
"""
Quick validation test for the fixed scraper
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from lead_gen_pipeline.scraper import HTMLScraper
    print("✅ Successfully imported HTMLScraper")
except ImportError as e:
    print(f"❌ Failed to import HTMLScraper: {e}")
    sys.exit(1)

# Test HTML samples from the test file
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

MOCK_B2B_HTML = """
<html>
<head>
    <title>TestBiz Solutions Inc. | Innovative Business Software</title>
    <meta name="description" content="TestBiz offers cutting-edge solutions for B2B needs. Contact us for more info.">
    <meta property="og:site_name" content="TestBiz Solutions Official">
    <link rel="canonical" href="http://mock-b2b-site.com/canonical-contact">
</head>
<body>
    <h1>Welcome to TestBiz Solutions</h1>
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

def test_basic_functionality():
    """Test basic scraper functionality"""
    print("\n🧪 Testing basic contact HTML...")
    
    scraper = HTMLScraper(SAMPLE_HTML_BASIC_CONTACT, "http://mycompany.com")
    data = scraper.scrape()
    
    print(f"Company name: {data.get('company_name')}")
    print(f"Emails: {data.get('emails', [])}")
    print(f"Phone numbers: {data.get('phone_numbers', [])}")
    print(f"Addresses: {data.get('addresses', [])}")
    print(f"Social media: {data.get('social_media_links', {})}")
    
    # Basic validation
    emails = data.get('emails', [])
    if 'info@mycompany.com' in emails:
        print("✅ Email extraction working")
    else:
        print(f"❌ Email extraction failed. Got: {emails}")
    
    social = data.get('social_media_links', {})
    if 'linkedin' in social and 'twitter' in social:
        print("✅ Social media extraction working")
    else:
        print(f"❌ Social media extraction failed. Got: {social}")

def test_mock_b2b():
    """Test mock B2B HTML"""
    print("\n🧪 Testing mock B2B HTML...")
    
    scraper = HTMLScraper(MOCK_B2B_HTML, "http://mock-b2b-site.com/contact")
    data = scraper.scrape()
    
    print(f"Company name: {data.get('company_name')}")
    print(f"Description: {data.get('description')}")
    print(f"Canonical URL: {data.get('canonical_url')}")
    print(f"Emails: {data.get('emails', [])}")
    print(f"Phone numbers: {data.get('phone_numbers', [])}")
    print(f"Social media: {data.get('social_media_links', {})}")
    
    # Validate key expectations
    if data.get('company_name') == 'TestBiz Solutions Official':
        print("✅ Company name extraction working")
    else:
        print(f"❌ Company name extraction failed. Expected 'TestBiz Solutions Official', got: {data.get('company_name')}")
    
    emails = data.get('emails', [])
    expected_emails = ['info@testbizsolutions.com', 'sales@testbizsolutions.com']
    if all(email in emails for email in expected_emails):
        print("✅ Email extraction working")
    else:
        print(f"❌ Email extraction failed. Expected {expected_emails}, got: {emails}")

def test_text_extraction():
    """Test text extraction edge cases"""
    print("\n🧪 Testing text extraction...")
    
    html = """
    <div>
    <p>Call <span>now: <b>1</b > - <em>800</em></span><span>-<span>TOLL</span><span>FREE</span></span> !</p>
    <p>Email:<span>info</span>@<span>example.com</span></p>
    </div>
    """
    
    scraper = HTMLScraper(html, "http://test.com")
    data = scraper.scrape()
    
    print(f"Extracted data: {data}")

if __name__ == "__main__":
    print("🚀 Starting scraper validation tests...")
    
    test_basic_functionality()
    test_mock_b2b() 
    test_text_extraction()
    
    print("\n✅ Validation tests complete!")
