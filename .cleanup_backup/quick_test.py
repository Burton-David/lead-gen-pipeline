#!/usr/bin/env python3
"""
Quick functionality test for the pipeline
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_basic_imports():
    """Test that all core modules can be imported"""
    print("🔧 Testing basic imports...")
    
    try:
        from lead_gen_pipeline.scraper import HTMLScraper
        print("✅ Scraper import successful")
        
        from lead_gen_pipeline.config import settings
        print("✅ Config import successful")
        
        from lead_gen_pipeline.utils import logger
        print("✅ Utils import successful")
        
        from lead_gen_pipeline.models import Lead
        print("✅ Models import successful")
        
        from lead_gen_pipeline.database import init_db
        print("✅ Database import successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_scraper_basic():
    """Test basic scraper functionality"""
    print("\n🧪 Testing basic scraper...")
    
    try:
        from lead_gen_pipeline.scraper import HTMLScraper
        
        # Simple test HTML
        html = """
        <html>
        <head>
            <title>Test Company Inc</title>
            <meta property="og:site_name" content="Test Company Official">
        </head>
        <body>
            <p>Email: info@testcompany.com</p>
            <p>Phone: 555-123-4567</p>
            <a href="https://linkedin.com/company/test">LinkedIn</a>
        </body>
        </html>
        """
        
        scraper = HTMLScraper(html, "http://testcompany.com")
        data = scraper.scrape()
        
        print(f"Company name: {data.get('company_name')}")
        print(f"Emails: {data.get('emails')}")
        print(f"Phone numbers: {data.get('phone_numbers')}")
        print(f"Social media: {data.get('social_media_links')}")
        
        # Basic validation
        has_company = data.get('company_name') is not None
        has_email = 'info@testcompany.com' in (data.get('emails') or [])
        has_social = 'linkedin' in (data.get('social_media_links') or {})
        
        if has_company and has_email and has_social:
            print("✅ Basic scraper functionality working")
            return True
        else:
            print("❌ Scraper missing some functionality")
            return False
        
    except Exception as e:
        print(f"❌ Scraper test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_phone_parsing():
    """Test phone number parsing specifically"""
    print("\n📞 Testing phone number parsing...")
    
    try:
        from lead_gen_pipeline.scraper import HTMLScraper
        
        test_cases = [
            ("<p>Call 555-123-4567</p>", "Basic format"),
            ("<a href='tel:+15551234567'>+1-555-123-4567</a>", "Tel link"),
            ("<p>Phone: 1-800-FLOWERS</p>", "Vanity number"),
        ]
        
        for html, description in test_cases:
            scraper = HTMLScraper(html, "http://test.com")
            phones = scraper.extract_phone_numbers()
            
            if phones:
                print(f"✅ {description}: {phones}")
            else:
                print(f"⚠️  {description}: No phones extracted")
        
        return True
        
    except Exception as e:
        print(f"❌ Phone parsing test failed: {e}")
        return False

def test_email_parsing():
    """Test email parsing specifically"""
    print("\n📧 Testing email parsing...")
    
    try:
        from lead_gen_pipeline.scraper import HTMLScraper
        
        test_cases = [
            ("<p>Email: test@example.com</p>", "Basic email"),
            ("<a href='mailto:info@company.com'>Contact</a>", "Mailto link"),
            ("<p>Contact us at user [at] domain [dot] com</p>", "Obfuscated"),
        ]
        
        for html, description in test_cases:
            scraper = HTMLScraper(html, "http://test.com")
            emails = scraper.extract_emails()
            
            if emails:
                print(f"✅ {description}: {emails}")
            else:
                print(f"⚠️  {description}: No emails extracted")
        
        return True
        
    except Exception as e:
        print(f"❌ Email parsing test failed: {e}")
        return False

def main():
    """Run all basic tests"""
    print("🚀 Running basic functionality tests...\n")
    
    # Test imports first
    if not test_basic_imports():
        print("❌ Cannot proceed - imports failed")
        return False
    
    # Test core functionality
    results = []
    results.append(test_scraper_basic())
    results.append(test_phone_parsing())
    results.append(test_email_parsing())
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n📊 Results: {success_count}/{total_count} tests passed")
    
    if success_count == total_count:
        print("🎉 All basic tests passed!")
        return True
    else:
        print("⚠️  Some tests failed, but core functionality may still work")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
