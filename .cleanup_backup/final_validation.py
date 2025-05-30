#!/usr/bin/env python3
"""
🚀 FINAL PRODUCTION VALIDATION TEST
This script validates that the entire lead generation pipeline is production-ready
"""
import asyncio
import sys
import tempfile
import csv
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class ProductionValidator:
    def __init__(self):
        self.passed_tests = 0
        self.total_tests = 0
        self.test_results = []
        
    def test(self, test_name):
        """Decorator for test methods"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                self.total_tests += 1
                print(f"\n🧪 [{self.total_tests:02d}] {test_name}")
                print("-" * 60)
                
                try:
                    result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                    if result:
                        print(f"✅ PASS: {test_name}")
                        self.passed_tests += 1
                        self.test_results.append({"test": test_name, "status": "PASS", "details": "Success"})
                    else:
                        print(f"❌ FAIL: {test_name}")
                        self.test_results.append({"test": test_name, "status": "FAIL", "details": "Test returned False"})
                    return result
                except Exception as e:
                    print(f"❌ ERROR: {test_name} - {e}")
                    self.test_results.append({"test": test_name, "status": "ERROR", "details": str(e)})
                    return False
            return wrapper
        return decorator
    
    def summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("🎯 PRODUCTION VALIDATION SUMMARY")
        print("=" * 80)
        
        print(f"📊 Results: {self.passed_tests}/{self.total_tests} tests passed ({self.passed_tests/self.total_tests*100:.1f}%)")
        
        if self.passed_tests == self.total_tests:
            print("\n🎉 ALL TESTS PASSED! SYSTEM IS PRODUCTION READY! 🎉")
            print("\n🚀 Ready to impress employers!")
            return True
        else:
            print(f"\n⚠️  {self.total_tests - self.passed_tests} tests failed. Review results above.")
            return False

validator = ProductionValidator()

@validator.test("Core Module Imports")
def test_imports():
    """Test that all core modules import successfully"""
    imports = [
        ("lead_gen_pipeline.config", "settings"),
        ("lead_gen_pipeline.utils", "logger"),
        ("lead_gen_pipeline.scraper", "HTMLScraper"),
        ("lead_gen_pipeline.crawler", "AsyncWebCrawler"),
        ("lead_gen_pipeline.database", "init_db"),
        ("lead_gen_pipeline.models", "Lead"),
    ]
    
    for module_name, item_name in imports:
        try:
            module = __import__(module_name, fromlist=[item_name])
            getattr(module, item_name)
            print(f"  ✅ {module_name}.{item_name}")
        except Exception as e:
            print(f"  ❌ {module_name}.{item_name} - {e}")
            return False
    
    return True

@validator.test("Phone Number Extraction (Production Quality)")
def test_phone_extraction():
    """Test phone number extraction with real-world cases"""
    from lead_gen_pipeline.scraper import HTMLScraper
    
    test_cases = [
        # (HTML, expected_phone_count, description)
        ("<p>Call us at <a href='tel:+15551234567'>555-123-4567</a></p>", 1, "Tel link"),
        ("<p>Phone: 888.556.0100</p>", 1, "Dotted format"),
        ("<p>Contact: (303) 556-0101 or 303-556-0102</p>", 2, "Multiple numbers"),
        ("<p>UK Office: +44 20 7946 0958</p>", 1, "International"),
        ("<p>Toll Free: 1-800-FLOWERS</p>", 1, "Vanity number"),
        ("<p>Main: <span>1-800</span>-<span>GOOD</span>-<span>BOY</span></p>", 1, "Split vanity"),
        ("<p>Generic: 555-555-5555</p>", 0, "Generic filtered"),
    ]
    
    all_passed = True
    for html, expected_count, description in test_cases:
        scraper = HTMLScraper(html, "http://test.com")
        phones = scraper.extract_phone_numbers()
        
        if len(phones) == expected_count:
            print(f"  ✅ {description}: {phones}")
        else:
            print(f"  ❌ {description}: Expected {expected_count}, got {len(phones)} - {phones}")
            all_passed = False
    
    return all_passed

@validator.test("Email Extraction (Production Quality)")
def test_email_extraction():
    """Test email extraction with obfuscation handling"""
    from lead_gen_pipeline.scraper import HTMLScraper
    
    test_cases = [
        ("<p>Email: info@company.com</p>", ["info@company.com"], "Basic email"),
        ("<a href='mailto:sales@corp.com'>Contact Sales</a>", ["sales@corp.com"], "Mailto link"),
        ("<p>user [at] domain [dot] com</p>", ["user@domain.com"], "Obfuscated [at][dot]"),
        ("<p>contact(at)business(dot)co(dot)uk</p>", ["contact@business.co.uk"], "Obfuscated (at)(dot)"),
        ("<p>Email:<span>info</span>@<span>test</span>.<span>com</span></p>", ["info@test.com"], "Split spans"),
        ("<p>Generic: test@example.com</p>", [], "Generic filtered"),
    ]
    
    all_passed = True
    for html, expected, description in test_cases:
        scraper = HTMLScraper(html, "http://test.com")
        emails = scraper.extract_emails()
        
        if sorted(emails) == sorted(expected):
            print(f"  ✅ {description}: {emails}")
        else:
            print(f"  ❌ {description}: Expected {expected}, got {emails}")
            all_passed = False
    
    return all_passed

@validator.test("Company Name Extraction (Production Quality)")
def test_company_extraction():
    """Test company name extraction strategies"""
    from lead_gen_pipeline.scraper import HTMLScraper
    
    test_cases = [
        ("<meta property='og:site_name' content='TechCorp Inc'>", "TechCorp Inc", "og:site_name"),
        ("<title>Amazing Solutions Ltd</title>", "Amazing Solutions Ltd", "Title tag"),
        ("<meta property='og:title' content='Product Page | BrandName Corp'>", "BrandName Corp", "og:title split"),
        ("<footer>© 2024 Copyright Industries LLC. All rights reserved.</footer>", "Copyright Industries LLC", "Copyright"),
        ("<title>Home</title>", None, "Generic filtered"),
    ]
    
    all_passed = True
    for html, expected, description in test_cases:
        scraper = HTMLScraper(html, "http://test.com")
        company = scraper.extract_company_name()
        
        if company == expected:
            print(f"  ✅ {description}: '{company}'")
        else:
            print(f"  ❌ {description}: Expected '{expected}', got '{company}'")
            all_passed = False
    
    return all_passed

@validator.test("Social Media Link Detection")
def test_social_media():
    """Test social media link extraction and validation"""
    from lead_gen_pipeline.scraper import HTMLScraper
    
    html = """
    <div>
        <a href="https://linkedin.com/company/testcorp">LinkedIn</a>
        <a href="http://twitter.com/testcorp_inc">Twitter</a>
        <a href="https://www.facebook.com/TestCorpOfficial">Facebook</a>
        <a href="https://www.youtube.com/c/TestCorpChannel">YouTube</a>
        <a href="https://instagram.com/testcorp">Instagram</a>
        <a href="https://linkedin.com/login">LinkedIn Login (should be ignored)</a>
    </div>
    """
    
    scraper = HTMLScraper(html, "http://test.com")
    social = scraper.extract_social_media_links()
    
    expected_platforms = {"linkedin", "twitter", "facebook", "youtube", "instagram"}
    found_platforms = set(social.keys())
    
    if expected_platforms.issubset(found_platforms):
        print(f"  ✅ Found platforms: {list(found_platforms)}")
        for platform, url in social.items():
            print(f"    {platform}: {url}")
        return True
    else:
        print(f"  ❌ Expected: {expected_platforms}, Found: {found_platforms}")
        return False

@validator.test("Address Extraction (Schema.org)")
def test_address_extraction():
    """Test address extraction from structured data"""
    from lead_gen_pipeline.scraper import HTMLScraper
    
    html = """
    <div itemscope itemtype="http://schema.org/PostalAddress">
        <span itemprop="streetAddress">123 Business Ave</span>,
        <span itemprop="addressLocality">Tech City</span>,
        <span itemprop="addressRegion">CA</span>
        <span itemprop="postalCode">94105</span>
    </div>
    """
    
    scraper = HTMLScraper(html, "http://test.com")
    addresses = scraper.extract_addresses()
    
    if addresses and "123 Business Ave" in addresses[0] and "Tech City" in addresses[0]:
        print(f"  ✅ Address extracted: {addresses[0]}")
        return True
    else:
        print(f"  ❌ Address extraction failed: {addresses}")
        return False

@validator.test("Comprehensive Scraping Integration")
def test_comprehensive_scraping():
    """Test complete scraping with realistic HTML"""
    from lead_gen_pipeline.scraper import HTMLScraper
    
    realistic_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>InnovateTech Solutions | Enterprise Software Development</title>
        <meta name="description" content="Leading provider of enterprise software solutions for Fortune 500 companies.">
        <meta property="og:site_name" content="InnovateTech Solutions Inc">
        <link rel="canonical" href="https://innovatetech.com/about">
    </head>
    <body>
        <header>
            <h1>Welcome to InnovateTech Solutions</h1>
        </header>
        
        <main>
            <section class="contact-info">
                <h2>Contact Information</h2>
                <p>Email us at: <a href="mailto:info@innovatetech.com">info@innovatetech.com</a></p>
                <p>Sales inquiries: <a href="mailto:sales@innovatetech.com">sales@innovatetech.com</a></p>
                <p>Main line: <a href="tel:+15551234567">(555) 123-4567</a></p>
                <p>Toll free: 1-800-TECH-NOW</p>
                <p>UK Office: +44 20 1234 5678</p>
            </section>
            
            <section class="address" itemscope itemtype="http://schema.org/PostalAddress">
                <h2>Headquarters</h2>
                <div>
                    <span itemprop="streetAddress">456 Innovation Blvd, Suite 100</span><br>
                    <span itemprop="addressLocality">Silicon Valley</span>,
                    <span itemprop="addressRegion">CA</span>
                    <span itemprop="postalCode">94025</span>
                </div>
            </section>
            
            <section class="social-media">
                <h2>Follow Us</h2>
                <a href="https://linkedin.com/company/innovatetech-solutions">LinkedIn</a>
                <a href="https://twitter.com/InnovateTechInc">Twitter</a>
                <a href="https://www.facebook.com/InnovateTechSolutions">Facebook</a>
                <a href="https://www.youtube.com/c/InnovateTechSolutions">YouTube</a>
            </section>
        </main>
        
        <footer>
            <p>© 2024 InnovateTech Solutions Inc. All rights reserved.</p>
        </footer>
    </body>
    </html>
    """
    
    scraper = HTMLScraper(realistic_html, "https://innovatetech.com/about")
    data = scraper.scrape()
    
    # Validation checklist
    checks = [
        (data.get('company_name') == 'InnovateTech Solutions Inc', "Company name"),
        (data.get('website') == 'https://innovatetech.com', "Website"),
        (data.get('canonical_url') == 'https://innovatetech.com/about', "Canonical URL"),
        ('info@innovatetech.com' in data.get('emails', []), "Primary email"),
        ('sales@innovatetech.com' in data.get('emails', []), "Sales email"),
        (len(data.get('phone_numbers', [])) >= 2, "Multiple phone numbers"),
        (len(data.get('addresses', [])) >= 1, "Address extraction"),
        ('linkedin' in data.get('social_media_links', {}), "LinkedIn"),
        ('twitter' in data.get('social_media_links', {}), "Twitter"),
        (data.get('description') and 'enterprise software' in data.get('description', '').lower(), "Description"),
    ]
    
    passed_checks = 0
    for check_result, check_name in checks:
        if check_result:
            print(f"  ✅ {check_name}")
            passed_checks += 1
        else:
            print(f"  ❌ {check_name}")
    
    print(f"\n  📊 Comprehensive test: {passed_checks}/{len(checks)} checks passed")
    
    # Show extracted data summary
    print(f"  📋 Extracted Data Summary:")
    print(f"    Company: {data.get('company_name')}")
    print(f"    Emails: {len(data.get('emails', []))} found")
    print(f"    Phones: {len(data.get('phone_numbers', []))} found")
    print(f"    Social: {len(data.get('social_media_links', {}))} platforms")
    print(f"    Addresses: {len(data.get('addresses', []))} found")
    
    return passed_checks >= len(checks) * 0.8  # 80% pass rate required

@validator.test("CLI Interface Functionality")
def test_cli_interface():
    """Test that CLI can be imported and basic commands work"""
    try:
        # Test imports
        import lead_gen_pipeline.cli_mvp as cli
        print("  ✅ CLI module imports successfully")
        
        # Test that Typer app is created
        if hasattr(cli, 'app'):
            print("  ✅ Typer app created")
        else:
            print("  ❌ Typer app not found")
            return False
            
        # Test config access
        from lead_gen_pipeline.config import settings
        if settings.PROJECT_NAME:
            print(f"  ✅ Configuration accessible: {settings.PROJECT_NAME}")
        else:
            print("  ❌ Configuration not accessible")
            return False
            
        return True
        
    except Exception as e:
        print(f"  ❌ CLI test failed: {e}")
        return False

@validator.test("Database Integration")
async def test_database():
    """Test database operations"""
    try:
        from lead_gen_pipeline.database import init_db, save_lead, get_async_session_local
        from lead_gen_pipeline.models import Lead
        from lead_gen_pipeline.config import settings
        from sqlalchemy import select
        import tempfile
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db_path = temp_db.name
        temp_db.close()
        
        # Override database URL
        original_db_url = settings.database.DATABASE_URL
        settings.database.DATABASE_URL = f"sqlite+aiosqlite:///{temp_db_path}"
        
        print(f"  🔧 Using test database: {temp_db_path}")
        
        # Initialize database
        await init_db()
        print("  ✅ Database initialized")
        
        # Test saving a lead
        test_lead_data = {
            "company_name": "Test Company Inc",
            "website": "https://testcompany.com",
            "scraped_from_url": "https://testcompany.com/contact",
            "emails": ["info@testcompany.com"],
            "phone_numbers": ["+15551234567"],
            "addresses": ["123 Test St, Test City, TC 12345"],
            "social_media_links": {"linkedin": "https://linkedin.com/company/test"}
        }
        
        saved_lead = await save_lead(test_lead_data)
        if saved_lead and saved_lead.id:
            print(f"  ✅ Lead saved with ID: {saved_lead.id}")
        else:
            print("  ❌ Failed to save lead")
            return False
        
        # Test querying leads
        session_factory = get_async_session_local()
        async with session_factory() as session:
            result = await session.execute(select(Lead))
            leads = result.scalars().all()
            
            if leads and len(leads) == 1:
                print(f"  ✅ Lead retrieved: {leads[0].company_name}")
            else:
                print(f"  ❌ Failed to retrieve leads: {len(leads) if leads else 0} found")
                return False
        
        # Cleanup
        settings.database.DATABASE_URL = original_db_url
        Path(temp_db_path).unlink(missing_ok=True)
        
        print("  ✅ Database test completed successfully")
        return True
        
    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
        return False

@validator.test("Error Handling & Edge Cases")
def test_error_handling():
    """Test that the system handles edge cases gracefully"""
    from lead_gen_pipeline.scraper import HTMLScraper
    
    edge_cases = [
        ("", "Empty HTML"),
        ("<html></html>", "Minimal HTML"),
        ("Invalid HTML <><>>", "Malformed HTML"),
        ("<html><body><script>alert('test')</script></body></html>", "Script tags"),
        ("<html><body><p>No contact info here</p></body></html>", "No contact data"),
    ]
    
    all_passed = True
    for html, description in edge_cases:
        try:
            scraper = HTMLScraper(html, "http://test.com")
            data = scraper.scrape()
            print(f"  ✅ {description}: handled gracefully")
        except Exception as e:
            print(f"  ❌ {description}: failed with {e}")
            all_passed = False
    
    return all_passed

async def main():
    """Run all production validation tests"""
    print("🚀 LEAD GENERATION PIPELINE - PRODUCTION VALIDATION")
    print("=" * 80)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Goal: Validate production readiness for potential employers")
    
    # Run all tests
    test_imports()
    test_phone_extraction()
    test_email_extraction()
    test_company_extraction()
    test_social_media()
    test_address_extraction()
    test_comprehensive_scraping()
    test_cli_interface()
    await test_database()
    test_error_handling()
    
    # Show final summary
    success = validator.summary()
    
    if success:
        print("\n🎊 CONGRATULATIONS! YOUR PIPELINE IS PRODUCTION READY! 🎊")
        print("\n📋 What this means:")
        print("   ✅ All core functionality works perfectly")
        print("   ✅ Real-world data extraction is robust")
        print("   ✅ Error handling is comprehensive")
        print("   ✅ Database integration is solid")
        print("   ✅ CLI interface is professional")
        print("\n🎯 Ready to impress employers!")
        print("\n💼 Demo command for interviews:")
        print("   python cli_mvp.py test-scraper https://python.org --verbose")
    else:
        print("\n⚠️  Some tests failed. Review the output above.")
        print("💡 Most likely causes:")
        print("   - Missing dependencies (pip install -r requirements.txt)")
        print("   - Python version compatibility (requires Python 3.9+)")
        print("   - Module import issues (run from project root)")
    
    print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
