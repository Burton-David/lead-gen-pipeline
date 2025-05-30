#!/usr/bin/env python3
"""
Comprehensive test validation for the fixed scraper
Tests key scenarios from the unit test file to ensure our fixes work
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent 
sys.path.insert(0, str(project_root))

def test_phone_number_extraction():
    """Test phone number extraction with key patterns from tests"""
    from lead_gen_pipeline.scraper import HTMLScraper
    
    print("🧪 Testing phone number extraction...")
    
    test_cases = [
        # Test case: (HTML, expected_phones, description)
        ("<p>Call us at <a href='tel:18005551212'>1-800-555-1212</a></p>", ["+18005551212"], "Simple tel link"),
        ("<p>Phone: 888.556.0100</p>", ["+18885560100"], "Plain text with dots"),
        ("<div>Contact: (303) 556-0101 or 303-556-0102</div>", ["+13035560101", "+13035560102"], "Multiple numbers"),
        ("<p>Tel. +44 20 7946 0958</p>", ["+442079460958"], "International UK number"),
        ("<span>Main: 1-800-GOOD-BOY</span>", ["+18004663269"], "Vanity number"),
        ("Phone: <span>1-800</span>-<span>FLOWERS</span>", ["+18003569377"], "Split vanity number"),
    ]
    
    for html, expected, description in test_cases:
        try:
            scraper = HTMLScraper(html, "http://test.com")
            phones = scraper.extract_phone_numbers()
            
            if sorted(phones) == sorted(expected):
                print(f"✅ {description}")
            else:
                print(f"❌ {description} - Expected: {expected}, Got: {phones}")
        except Exception as e:
            print(f"❌ {description} - Error: {e}")

def test_email_extraction():
    """Test email extraction with key patterns"""
    from lead_gen_pipeline.scraper import HTMLScraper
    
    print("\n🧪 Testing email extraction...")
    
    test_cases = [
        ("<p>Email: test@example.com. Also TEST@EXAMPLE.COM.</p>", ["test@example.com"], "Plain text with dedup"),
        ("<p>info [at] example [dot] com</p>", ["info@example.com"], "Obfuscated [at] [dot]"),
        ("Contact us: user(at)domain(dot)co(dot)uk", ["user@domain.co.uk"], "Obfuscated (at) (dot)"),
        ("Email:<span>info</span>@<span>example.com</span>", ["info@example.com"], "Split in spans"),
    ]
    
    for html, expected, description in test_cases:
        try:
            scraper = HTMLScraper(html, "http://test.com")
            emails = scraper.extract_emails()
            
            if sorted(emails) == sorted(expected):
                print(f"✅ {description}")
            else:
                print(f"❌ {description} - Expected: {expected}, Got: {emails}")
        except Exception as e:
            print(f"❌ {description} - Error: {e}")

def test_company_name_extraction():
    """Test company name extraction"""
    from lead_gen_pipeline.scraper import HTMLScraper
    
    print("\n🧪 Testing company name extraction...")
    
    test_cases = [
        ("<meta property=\"og:site_name\" content=\"Test Company Inc\">", "Test Company Inc", "og:site_name"),
        ("<title>My Awesome Company</title>", "My Awesome Company", "Title tag"),
        ("<meta property=\"og:title\" content=\"Product | BrandName\">", "BrandName", "og:title with separator"),
        ("<footer>© 2024 Copyright Holder Inc.</footer>", "Copyright Holder Inc.", "Copyright footer"),
    ]
    
    for html, expected, description in test_cases:
        try:
            scraper = HTMLScraper(html, "http://test.com")
            company_name = scraper.extract_company_name()
            
            if company_name == expected:
                print(f"✅ {description}")
            else:
                print(f"❌ {description} - Expected: {expected}, Got: {company_name}")
        except Exception as e:
            print(f"❌ {description} - Error: {e}")

def test_social_media_extraction():
    """Test social media link extraction"""
    from lead_gen_pipeline.scraper import HTMLScraper
    
    print("\n🧪 Testing social media extraction...")
    
    html = """
    <div>
        <a href="https://linkedin.com/company/testbiz">LinkedIn</a>
        <a href="http://twitter.com/testbizinc">Twitter</a>
        <a href="https://www.facebook.com/TestBizSolutions">Facebook</a>
        <a href="https://www.youtube.com/testbiz">YouTube</a>
    </div>
    """
    
    try:
        scraper = HTMLScraper(html, "http://test.com")
        social_links = scraper.extract_social_media_links()
        
        expected_platforms = ["linkedin", "twitter", "facebook", "youtube"]
        found_platforms = list(social_links.keys())
        
        if all(platform in found_platforms for platform in expected_platforms):
            print("✅ Social media extraction working")
            for platform, url in social_links.items():
                print(f"   {platform}: {url}")
        else:
            print(f"❌ Social media extraction - Expected: {expected_platforms}, Got: {found_platforms}")
            
    except Exception as e:
        print(f"❌ Social media extraction - Error: {e}")

def test_comprehensive_scraping():
    """Test comprehensive scraping with mock B2B HTML"""
    from lead_gen_pipeline.scraper import HTMLScraper
    
    print("\n🧪 Testing comprehensive scraping...")
    
    mock_html = """
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
            <p>Email us at: <a href="mailto:info@testbizsolutions.com">info@testbizsolutions.com</a></p>
            <p>Or Sales: sales@testbizsolutions.com for quotes.</p>
            <p>Call us: <a href="tel:+15550123567">+1 (555) 012-3567</a> (Main)</p>
            <p>Support Line: 556-123-4567</p>
        </div>
        <div class="address" itemscope itemtype="http://schema.org/PostalAddress">
            <span itemprop="streetAddress">123 Innovation Drive</span>,
            <span itemprop="addressLocality">Tech City</span>,
            <span itemprop="addressRegion">TS</span>
            <span itemprop="postalCode">90210</span>
        </div>
        <div class="social-media">
            <a href="https://linkedin.com/company/testbiz">Our LinkedIn</a>
            <a href="http://twitter.com/testbizinc">Follow on Twitter</a>
        </div>
    </body>
    </html>
    """
    
    try:
        scraper = HTMLScraper(mock_html, "http://mock-b2b-site.com/contact")
        data = scraper.scrape()
        
        print(f"Company: {data.get('company_name')}")
        print(f"Description: {data.get('description')}")
        print(f"Website: {data.get('website')}")
        print(f"Canonical: {data.get('canonical_url')}")
        print(f"Emails: {data.get('emails', [])}")
        print(f"Phones: {data.get('phone_numbers', [])}")
        print(f"Addresses: {data.get('addresses', [])}")
        print(f"Social: {data.get('social_media_links', {})}")
        
        # Validate key fields
        checks = [
            (data.get('company_name') == 'TestBiz Solutions Official', "Company name"),
            ('info@testbizsolutions.com' in data.get('emails', []), "Primary email"),
            ('sales@testbizsolutions.com' in data.get('emails', []), "Sales email"),
            (len(data.get('phone_numbers', [])) >= 1, "Phone numbers"),
            ('linkedin' in data.get('social_media_links', {}), "LinkedIn"),
            ('twitter' in data.get('social_media_links', {}), "Twitter"),
            (data.get('canonical_url') == 'http://mock-b2b-site.com/canonical-contact', "Canonical URL"),
        ]
        
        for check_result, check_name in checks:
            if check_result:
                print(f"✅ {check_name}")
            else:
                print(f"❌ {check_name}")
                
    except Exception as e:
        print(f"❌ Comprehensive scraping - Error: {e}")

def main():
    """Run all validation tests"""
    print("🚀 Starting comprehensive scraper validation...\n")
    
    test_phone_number_extraction()
    test_email_extraction()
    test_company_name_extraction()
    test_social_media_extraction()
    test_comprehensive_scraping()
    
    print("\n✅ Validation tests completed!")

if __name__ == "__main__":
    main()
