#!/usr/bin/env python3
# test_without_llm.py - Test pipeline components without LLM dependency

import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

async def test_basic_scraping():
    """Test basic web scraping without LLM."""
    print("🧪 Testing basic web scraping (no LLM required)...")
    
    try:
        from lead_gen_pipeline.crawler import AsyncWebCrawler
        from lead_gen_pipeline.scraper import HTMLScraper
        
        print("✅ Successfully imported crawler and scraper")
        
        # Test web crawling
        crawler = AsyncWebCrawler()
        print("✅ Created web crawler instance")
        
        # Test fetching a simple page
        test_url = "https://www.paloaltochamber.com"
        print(f"🔍 Fetching: {test_url}")
        
        html_content, status_code, final_url = await crawler.fetch_page(test_url)
        
        if html_content and status_code == 200:
            print(f"✅ Successfully fetched page (status: {status_code})")
            print(f"   Final URL: {final_url}")
            print(f"   Content length: {len(html_content)} characters")
            
            # Test HTML scraping
            scraper = HTMLScraper(html_content, final_url)
            data = scraper.scrape()
            
            print("✅ Successfully scraped data:")
            print(f"   Company name: {data.get('company_name', 'Not found')}")
            print(f"   Emails found: {len(data.get('emails', []))}")
            print(f"   Phones found: {len(data.get('phone_numbers', []))}")
            print(f"   Addresses found: {len(data.get('addresses', []))}")
            
            await crawler.close()
            return True
        else:
            print(f"❌ Failed to fetch page (status: {status_code})")
            await crawler.close()
            return False
            
    except Exception as e:
        print(f"❌ Error in basic scraping test: {e}")
        return False

async def test_database_operations():
    """Test database operations."""
    print("\n🧪 Testing database operations...")
    
    try:
        from lead_gen_pipeline.database import init_db, get_async_session_local
        from lead_gen_pipeline.models import Lead
        from sqlalchemy import select
        
        print("✅ Successfully imported database modules")
        
        # Initialize database
        await init_db()
        print("✅ Database initialized")
        
        # Test session creation
        session_factory = get_async_session_local()
        async with session_factory() as session:
            # Query existing leads
            result = await session.execute(select(Lead))
            leads = result.scalars().all()
            print(f"✅ Found {len(leads)} existing leads in database")
            
        return True
        
    except Exception as e:
        print(f"❌ Error in database test: {e}")
        return False

async def test_bulk_database():
    """Test bulk database operations."""
    print("\n🧪 Testing bulk database operations...")
    
    try:
        from lead_gen_pipeline.bulk_database import BulkDatabaseProcessor
        
        # Create some test data
        test_businesses = [
            {
                'name': 'Test Company Alpha',
                'website': 'https://alpha.example.com',
                'phone': '+1-555-0001',
                'email': 'info@alpha.example.com',
                'address': '123 Test St, Test City, CA 94000',
                'industry': 'Technology'
            },
            {
                'name': 'Test Company Beta',
                'website': 'https://beta.example.com',
                'phone': '+1-555-0002',
                'email': 'contact@beta.example.com',
                'address': '456 Demo Ave, Demo City, CA 94001',
                'industry': 'Services'
            }
        ]
        
        test_chamber_info = {
            'name': 'Test Chamber of Commerce',
            'website': 'https://test-chamber.example.com'
        }
        
        # Test bulk processor
        processor = BulkDatabaseProcessor(batch_size=10)
        print("✅ Created bulk database processor")
        
        # Test bulk insert
        stats = await processor.bulk_insert_businesses(
            test_businesses, test_chamber_info, update_existing=True
        )
        
        print("✅ Bulk insert completed:")
        print(f"   Successful inserts: {stats.successful_inserts}")
        print(f"   Successful updates: {stats.successful_updates}")
        print(f"   Processing rate: {stats.records_per_second:.1f} records/sec")
        
        # Test database statistics
        db_stats = await processor.get_database_statistics()
        print("✅ Database statistics retrieved:")
        print(f"   Total leads: {db_stats.get('total_leads', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in bulk database test: {e}")
        return False

def test_cli_without_chambers():
    """Test CLI commands that don't require LLM."""
    print("\n🧪 Testing CLI commands (no LLM required)...")
    
    try:
        import subprocess
        
        # Test stats command
        print("Testing 'python cli.py stats'...")
        result = subprocess.run(['python', 'cli.py', 'stats'], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Stats command works")
        else:
            print(f"❌ Stats command failed: {result.stderr}")
        
        # Test config command
        print("Testing 'python cli.py config'...")
        result = subprocess.run(['python', 'cli.py', 'config'], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Config command works")
        else:
            print(f"❌ Config command failed: {result.stderr}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in CLI test: {e}")
        return False

async def main():
    """Run all non-LLM tests."""
    print("🚀 B2B Intelligence Platform - Component Testing (No LLM)")
    print("="*60)
    print("Testing individual components that don't require LLM...")
    print()
    
    results = []
    
    # Test basic scraping
    results.append(await test_basic_scraping())
    
    # Test database operations
    results.append(await test_database_operations())
    
    # Test bulk database operations  
    results.append(await test_bulk_database())
    
    # Test CLI commands
    results.append(test_cli_without_chambers())
    
    # Summary
    print("\n" + "="*60)
    print("🧪 Test Results Summary")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All non-LLM components are working correctly!")
        print("The issue is specifically with llama-cpp-python installation.")
        print("\nNext steps:")
        print("1. Run: python diagnostic_tests.py")
        print("2. Run: python fix_installation.py")
        print("3. Once LLM is fixed, chamber processing will work")
    else:
        print("❌ Some components have issues beyond the LLM problem.")
        print("Please review the errors above and fix them first.")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Testing interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Testing failed: {e}")
        sys.exit(1)
