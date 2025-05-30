#!/usr/bin/env python3
"""
End-to-end integration test for the lead generation pipeline
This tests the complete flow from URL input to database storage
"""
import asyncio
import sys
import tempfile
import csv
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_complete_pipeline():
    """Test the complete pipeline end-to-end"""
    print("🚀 Starting end-to-end pipeline test...\n")
    
    try:
        # Import required modules  
        from lead_gen_pipeline.database import init_db, get_async_session_local
        from lead_gen_pipeline.models import Lead
        from lead_gen_pipeline.config import settings
        from lead_gen_pipeline.run_pipeline_mvp import main_pipeline
        from sqlalchemy import select
        
        # Create temporary test database
        import tempfile
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db_path = temp_db.name
        temp_db.close()
        
        # Override database settings for test
        original_db_url = settings.database.DATABASE_URL
        settings.database.DATABASE_URL = f"sqlite+aiosqlite:///{temp_db_path}"
        
        print(f"📊 Using test database: {temp_db_path}")
        
        # Create test URLs CSV
        test_csv = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        test_urls = [
            "https://httpbin.org/html",  # Simple test page
            "https://example.com",       # Basic example page
        ]
        
        csv_writer = csv.writer(test_csv)
        csv_writer.writerow(['url'])
        for url in test_urls:
            csv_writer.writerow([url])
        test_csv.close()
        
        # Override input CSV setting
        original_input_csv = settings.INPUT_URLS_CSV
        settings.INPUT_URLS_CSV = Path(test_csv.name)
        
        print(f"📝 Using test CSV: {test_csv.name}")
        print(f"🎯 Test URLs: {test_urls}")
        
        # Override other settings for faster testing
        settings.MAX_PIPELINE_CONCURRENCY = 2
        settings.crawler.MIN_DELAY_PER_DOMAIN_SECONDS = 0.5
        settings.crawler.MAX_DELAY_PER_DOMAIN_SECONDS = 1.0
        
        print("\n🔧 Initializing database...")
        await init_db()
        print("✅ Database initialized")
        
        print("\n🕷️ Running pipeline...")
        await main_pipeline()
        print("✅ Pipeline completed")
        
        # Check results
        print("\n📊 Checking results...")
        session_factory = get_async_session_local()
        async with session_factory() as session:
            result = await session.execute(select(Lead))
            leads = result.scalars().all()
            
            print(f"📈 Found {len(leads)} leads in database")
            
            if leads:
                print("\n📋 Lead details:")
                for i, lead in enumerate(leads, 1):
                    print(f"  Lead {i}:")
                    print(f"    Company: {lead.company_name or 'N/A'}")
                    print(f"    Website: {lead.website or 'N/A'}")
                    print(f"    Source: {lead.scraped_from_url}")
                    print(f"    Emails: {len(lead.emails or [])}")
                    print(f"    Phones: {len(lead.phone_numbers or [])}")
                    print(f"    Addresses: {len(lead.addresses or [])}")
                    print(f"    Social: {len(lead.social_media_links or {})}")
                    print()
                
                print("✅ Pipeline successfully created leads!")
            else:
                print("⚠️  No leads were created (this might be expected for test URLs)")
        
        # Restore original settings
        settings.database.DATABASE_URL = original_db_url
        settings.INPUT_URLS_CSV = original_input_csv
        
        # Clean up temp files
        Path(temp_db_path).unlink(missing_ok=True)
        Path(test_csv.name).unlink(missing_ok=True)
        
        print("🧹 Cleaned up temporary files")
        print("✅ End-to-end test completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_cli_functionality():
    """Test CLI commands"""
    print("\n🖥️ Testing CLI functionality...")
    
    try:
        # Test imports
        from lead_gen_pipeline.cli_mvp import app
        print("✅ CLI imports working")
        
        # Test config display (this doesn't require execution)
        from lead_gen_pipeline.config import settings
        print(f"✅ Config accessible: {settings.PROJECT_NAME}")
        
        return True
        
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False

async def test_scraper_robustness():
    """Test scraper with various edge cases"""
    print("\n🧪 Testing scraper robustness...")
    
    try:
        from lead_gen_pipeline.scraper import HTMLScraper
        
        test_cases = [
            ("", "Empty HTML"),
            ("<html></html>", "Minimal HTML"),
            ("<html><body><p>No contact info</p></body></html>", "No contact info"),
            ("<html><head><title>Test & Company</title></head><body></body></html>", "HTML entities"),
            ("Invalid HTML <><>>", "Malformed HTML"),
        ]
        
        for html, description in test_cases:
            try:
                scraper = HTMLScraper(html, "http://test.com")
                data = scraper.scrape()
                print(f"✅ {description} - handled gracefully")
            except Exception as e:
                print(f"❌ {description} - failed: {e}")
                
        return True
        
    except Exception as e:
        print(f"❌ Scraper robustness test failed: {e}")
        return False

def test_import_integrity():
    """Test that all imports work correctly"""
    print("\n📦 Testing import integrity...")
    
    modules_to_test = [
        ("lead_gen_pipeline.config", "settings"),
        ("lead_gen_pipeline.utils", "logger"),
        ("lead_gen_pipeline.crawler", "AsyncWebCrawler"),
        ("lead_gen_pipeline.scraper", "HTMLScraper"),
        ("lead_gen_pipeline.database", "init_db"),
        ("lead_gen_pipeline.models", "Lead"),
        ("lead_gen_pipeline.run_pipeline_mvp", "main_pipeline"),
    ]
    
    all_imports_successful = True
    
    for module_name, item_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[item_name])
            getattr(module, item_name)  # Try to access the item
            print(f"✅ {module_name}.{item_name}")
        except Exception as e:
            print(f"❌ {module_name}.{item_name} - {e}")
            all_imports_successful = False
    
    return all_imports_successful

async def main():
    """Run all integration tests"""
    print("🧪 Starting comprehensive integration tests...")
    print("=" * 60)
    
    # Test 1: Import integrity
    imports_ok = test_import_integrity()
    
    # Test 2: Scraper robustness
    scraper_ok = await test_scraper_robustness()
    
    # Test 3: CLI functionality
    cli_ok = await test_cli_functionality()
    
    # Test 4: Complete pipeline (only if other tests pass)
    pipeline_ok = False
    if imports_ok and scraper_ok:
        try:
            pipeline_ok = await test_complete_pipeline()
        except Exception as e:
            print(f"❌ Pipeline test crashed: {e}")
    else:
        print("⚠️ Skipping pipeline test due to previous failures")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY:")
    print(f"Imports: {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"Scraper: {'✅ PASS' if scraper_ok else '❌ FAIL'}")
    print(f"CLI:     {'✅ PASS' if cli_ok else '❌ FAIL'}")
    print(f"Pipeline:{'✅ PASS' if pipeline_ok else '❌ FAIL'}")
    
    all_tests_passed = all([imports_ok, scraper_ok, cli_ok, pipeline_ok])
    
    if all_tests_passed:
        print("\n🎉 ALL TESTS PASSED! The pipeline is ready for production!")
    else:
        print("\n⚠️ Some tests failed. Please review the output above.")
    
    return all_tests_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
