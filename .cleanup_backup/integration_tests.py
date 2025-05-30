#!/usr/bin/env python3
# integration_tests.py - Integration test suite for B2B Intelligence Platform

import asyncio
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from lead_gen_pipeline.utils import logger
from lead_gen_pipeline.chamber_pipeline import ChamberPipeline
from lead_gen_pipeline.database import init_db, get_async_session_local
from lead_gen_pipeline.models import Lead
from sqlalchemy import select, func

async def test_llm_initialization():
    """Test LLM processor initialization."""
    logger.info("Testing LLM initialization...")
    
    try:
        from lead_gen_pipeline.llm_processor import get_llm_processor
        
        llm_processor = get_llm_processor()
        success = await llm_processor.initialize()
        
        if success:
            logger.success("✅ LLM initialized successfully")
            await llm_processor.close()
            return True
        else:
            logger.error("❌ LLM initialization failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ LLM test error: {e}")
        return False

async def test_database_operations():
    """Test database initialization and operations."""
    logger.info("Testing database operations...")
    
    try:
        await init_db()
        logger.success("✅ Database initialized")
        
        session_factory = get_async_session_local()
        async with session_factory() as session:
            result = await session.execute(select(func.count(Lead.id)))
            count = result.scalar()
            logger.success(f"✅ Database query successful - {count} records found")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test error: {e}")
        return False

async def test_single_chamber_processing():
    """Test processing a single chamber directory."""
    logger.info("Testing single chamber processing...")
    
    test_chamber_url = "https://www.paloaltochamber.com"
    
    try:
        pipeline = ChamberPipeline()
        
        success = await pipeline.initialize()
        if not success:
            logger.error("❌ Pipeline initialization failed")
            return False
        
        logger.success("✅ Pipeline initialized")
        
        logger.info(f"Processing test chamber: {test_chamber_url}")
        result = await pipeline.process_single_chamber(test_chamber_url)
        
        await pipeline.close()
        
        if result['success']:
            logger.success(f"✅ Chamber processed successfully")
            logger.success(f"   Chamber: {result.get('chamber_name', 'Unknown')}")
            logger.success(f"   Businesses found: {result.get('businesses_found', 0)}")
            logger.success(f"   Processing time: {result.get('processing_time', 0):.1f}s")
            return True
        else:
            logger.error(f"❌ Chamber processing failed: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Chamber processing test error: {e}")
        try:
            await pipeline.close()
        except:
            pass
        return False

async def test_database_operations_advanced():
    """Test advanced database save operations."""
    logger.info("Testing database save operations...")
    
    try:
        from lead_gen_pipeline.bulk_database import BulkDatabaseProcessor
        
        # Create test business data
        test_businesses = [
            {
                'name': 'Test Technology Solutions',
                'website': 'https://test-tech.example.com',
                'phone': '+1-555-0001',
                'email': 'info@test-tech.example.com',
                'address': '123 Innovation Dr, Tech City, CA 94000',
                'industry': 'Technology',
                'source_url': 'https://test-chamber.example.com'
            },
            {
                'name': 'Professional Services Inc',
                'website': 'https://pro-services.example.com',
                'phone': '+1-555-0002',
                'email': 'contact@pro-services.example.com',
                'address': '456 Business Ave, Commerce City, CA 94001',
                'industry': 'Professional Services',
                'source_url': 'https://test-chamber.example.com'
            }
        ]
        
        test_chamber_info = {
            'name': 'Test Chamber of Commerce',
            'website': 'https://test-chamber.example.com'
        }
        
        bulk_processor = BulkDatabaseProcessor(batch_size=100)
        stats = await bulk_processor.bulk_insert_businesses(
            test_businesses,
            test_chamber_info,
            update_existing=True
        )
        
        logger.success(f"✅ Bulk insert completed")
        logger.success(f"   Successful inserts: {stats.successful_inserts}")
        logger.success(f"   Processing rate: {stats.records_per_second:.1f} records/sec")
        
        db_stats = await bulk_processor.get_database_statistics()
        logger.success(f"✅ Database statistics retrieved")
        logger.success(f"   Total records: {db_stats.get('total_leads', 0)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database save test error: {e}")
        return False

async def run_integration_tests():
    """Run complete integration test suite."""
    logger.info("🚀 Starting B2B Intelligence Platform Integration Tests")
    logger.info("=" * 60)
    
    start_time = time.time()
    tests_passed = 0
    total_tests = 4
    
    # Test 1: LLM Initialization
    if await test_llm_initialization():
        tests_passed += 1
    
    # Test 2: Database Operations
    if await test_database_operations():
        tests_passed += 1
    
    # Test 3: Single Chamber Processing
    if await test_single_chamber_processing():
        tests_passed += 1
    
    # Test 4: Advanced Database Operations
    if await test_database_operations_advanced():
        tests_passed += 1
    
    # Summary
    elapsed_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info("🧪 Integration Test Results")
    logger.info("=" * 60)
    
    if tests_passed == total_tests:
        logger.success(f"✅ ALL TESTS PASSED ({tests_passed}/{total_tests})")
        logger.success(f"⏱️  Total test time: {elapsed_time:.1f} seconds")
        logger.success("🎉 B2B Intelligence Platform is ready for deployment!")
        return True
    else:
        logger.error(f"❌ SOME TESTS FAILED ({tests_passed}/{total_tests})")
        logger.error(f"⏱️  Total test time: {elapsed_time:.1f} seconds")
        logger.error("🔧 Please review failed tests and fix issues before deployment")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(run_integration_tests())
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.warning("🛑 Integration tests interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Integration test suite failed: {e}")
        sys.exit(1)
