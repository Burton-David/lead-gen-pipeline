# lead_gen_pipeline/chamber_pipeline.py
# Chamber directory processing orchestration

import asyncio
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
import csv

try:
    from .config import settings
    from .utils import logger
    from .chamber_parser import ChamberDirectoryParser
    from .bulk_database import BulkDatabaseProcessor
    from .database import init_db
except ImportError:
    from lead_gen_pipeline.config import settings
    from lead_gen_pipeline.utils import logger
    from lead_gen_pipeline.chamber_parser import ChamberDirectoryParser
    from lead_gen_pipeline.bulk_database import BulkDatabaseProcessor
    from lead_gen_pipeline.database import init_db

class ChamberPipeline:
    """Chamber directory processing pipeline orchestrator."""
    
    def __init__(self):
        self.chamber_parser: Optional[ChamberDirectoryParser] = None
        self.bulk_db_processor: Optional[BulkDatabaseProcessor] = None
        self.total_chambers_processed = 0
        self.total_businesses_extracted = 0
        self.start_time = time.time()
        
        logger.info("Chamber pipeline initialized")
    
    async def initialize(self) -> bool:
        """Initialize pipeline components."""
        try:
            logger.info("Initializing chamber directory pipeline...")
            
            await init_db()
            
            self.chamber_parser = ChamberDirectoryParser()
            parser_success = await self.chamber_parser.initialize()
            
            if not parser_success:
                logger.error("Failed to initialize chamber parser")
                return False
            
            self.bulk_db_processor = BulkDatabaseProcessor(batch_size=500)
            await self.bulk_db_processor.optimize_database()
            
            logger.success("Chamber pipeline initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize chamber pipeline: {e}")
            return False
    
    async def load_chamber_urls(self, csv_file_path: Optional[Path] = None) -> List[str]:
        """Load chamber URLs from CSV file."""
        csv_path = csv_file_path or settings.BASE_DIR / "data" / "chamber_urls.csv"
        
        if not csv_path.exists():
            logger.warning(f"Chamber URLs CSV not found: {csv_path}")
            logger.info("Creating sample chamber URLs file...")
            
            sample_chambers = [
                "https://www.paloaltochamber.com",
                "https://www.fremontbusiness.com", 
                "https://www.visitslo.com",
                "https://www.sanjosechamber.com",
                "https://www.oaklandchamber.com"
            ]
            
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['url', 'chamber_name', 'state'])
                for url in sample_chambers:
                    writer.writerow([url, '', ''])
            
            logger.info(f"Created sample chamber URLs file: {csv_path}")
        
        chamber_urls = []
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = row.get('url', '').strip()
                    if url and url.startswith(('http://', 'https://')):
                        chamber_urls.append(url)
            
            logger.info(f"Loaded {len(chamber_urls)} chamber URLs")
            return chamber_urls
            
        except Exception as e:
            logger.error(f"Error loading chamber URLs: {e}")
            return []
    
    async def process_single_chamber(self, chamber_url: str) -> Dict[str, Any]:
        """Process a single chamber directory."""
        if not self.chamber_parser:
            raise RuntimeError("Chamber parser not initialized")
        
        logger.info(f"Processing chamber: {chamber_url}")
        
        try:
            result = await self.chamber_parser.parse_chamber_directory(chamber_url)
            
            if result.success:
                self.total_chambers_processed += 1
                self.total_businesses_extracted += result.total_businesses_found
                
                logger.success(f"Successfully processed {result.chamber_info.get('name', 'Unknown Chamber')}")
                logger.success(f"   {result.total_businesses_found} businesses found")
                
                return {
                    'success': True,
                    'chamber_url': chamber_url,
                    'chamber_name': result.chamber_info.get('name', 'Unknown'),
                    'businesses_found': result.total_businesses_found,
                    'processing_time': result.processing_time_seconds,
                    'result': result
                }
            else:
                logger.error(f"Failed to process chamber: {chamber_url}")
                logger.error(f"   Error: {result.error_message}")
                
                return {
                    'success': False,
                    'chamber_url': chamber_url,
                    'error': result.error_message,
                    'result': result
                }
                
        except Exception as e:
            logger.error(f"Exception processing chamber {chamber_url}: {e}")
            return {
                'success': False,
                'chamber_url': chamber_url,
                'error': str(e),
                'result': None
            }
    
    async def process_chamber_batch(self, chamber_urls: List[str]) -> List[Dict[str, Any]]:
        """Process batch of chambers with concurrency control."""
        if not self.chamber_parser:
            raise RuntimeError("Chamber parser not initialized")
        
        logger.info(f"Processing batch of {len(chamber_urls)} chambers")
        
        results = await self.chamber_parser.parse_multiple_chambers(chamber_urls)
        
        summary_results = []
        for i, result in enumerate(results):
            chamber_url = chamber_urls[i]
            
            if result.success:
                summary_results.append({
                    'success': True,
                    'chamber_url': chamber_url,
                    'chamber_name': result.chamber_info.get('name', 'Unknown'),
                    'businesses_found': result.total_businesses_found,
                    'processing_time': result.processing_time_seconds,
                    'result': result
                })
                
                self.total_chambers_processed += 1
                self.total_businesses_extracted += result.total_businesses_found
            else:
                summary_results.append({
                    'success': False,
                    'chamber_url': chamber_url,
                    'error': result.error_message,
                    'result': result
                })
        
        return summary_results
    
    async def save_results_to_database(self, processing_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Save processing results to database."""
        if not self.bulk_db_processor:
            raise RuntimeError("Bulk database processor not initialized")
        
        logger.info("Saving results to database...")
        
        successful_results = [r['result'] for r in processing_results if r['success'] and r['result']]
        
        if not successful_results:
            logger.warning("No successful results to save")
            return {'success': False, 'message': 'No results to save'}
        
        try:
            stats = await self.bulk_db_processor.bulk_insert_chamber_results(
                successful_results,
                update_existing=True
            )
            
            db_stats = await self.bulk_db_processor.get_database_statistics()
            
            logger.success("Database save completed")
            logger.success(f"   Database now contains {db_stats.get('total_leads', 0)} total records")
            
            return {
                'success': True,
                'chamber_stats': stats,
                'database_stats': db_stats
            }
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            return {'success': False, 'error': str(e)}
    
    async def process_all_chambers(self, chamber_urls: Optional[List[str]] = None) -> Dict[str, Any]:
        """Process all chamber directories end-to-end."""
        pipeline_start_time = time.time()
        
        logger.info("Starting chamber directory pipeline")
        
        if chamber_urls is None:
            chamber_urls = await self.load_chamber_urls()
        
        if not chamber_urls:
            return {
                'success': False,
                'error': 'No chamber URLs to process'
            }
        
        logger.info(f"Processing {len(chamber_urls)} chambers total")
        
        # Process in manageable batches
        batch_size = 5
        all_results = []
        
        for i in range(0, len(chamber_urls), batch_size):
            batch = chamber_urls[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(chamber_urls) + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chambers)")
            
            try:
                batch_results = await self.process_chamber_batch(batch)
                all_results.extend(batch_results)
                
                logger.info(f"Saving batch {batch_num} results...")
                save_result = await self.save_results_to_database(batch_results)
                
                if save_result['success']:
                    logger.success(f"Batch {batch_num} saved successfully")
                else:
                    logger.error(f"Failed to save batch {batch_num}: {save_result.get('error')}")
                
                await asyncio.sleep(1)  # Brief pause between batches
                
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {e}")
                continue
        
        # Final statistics
        pipeline_time = time.time() - pipeline_start_time
        successful_chambers = sum(1 for r in all_results if r['success'])
        
        final_db_stats = await self.bulk_db_processor.get_database_statistics() if self.bulk_db_processor else {}
        
        summary = {
            'success': True,
            'total_chambers_attempted': len(chamber_urls),
            'successful_chambers': successful_chambers,
            'failed_chambers': len(chamber_urls) - successful_chambers,
            'total_businesses_extracted': self.total_businesses_extracted,
            'total_processing_time_seconds': pipeline_time,
            'processing_rate_chambers_per_hour': (successful_chambers / (pipeline_time / 3600)) if pipeline_time > 0 else 0,
            'database_stats': final_db_stats,
            'detailed_results': all_results
        }
        
        logger.success("Chamber directory pipeline completed!")
        logger.success(f"   Processed: {successful_chambers}/{len(chamber_urls)} chambers successfully")
        logger.success(f"   Total businesses extracted: {self.total_businesses_extracted}")
        logger.success(f"   Total time: {pipeline_time:.1f} seconds")
        logger.success(f"   Database total records: {final_db_stats.get('total_leads', 0)}")
        
        return summary
    
    async def close(self):
        """Clean up pipeline resources."""
        try:
            if self.chamber_parser:
                await self.chamber_parser.close()
            
            logger.info("Chamber pipeline resources cleaned up")
            
        except Exception as e:
            logger.error(f"Error cleaning up pipeline resources: {e}")


async def run_chamber_pipeline(chamber_urls: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run the complete chamber directory pipeline."""
    pipeline = ChamberPipeline()
    
    try:
        success = await pipeline.initialize()
        if not success:
            return {'success': False, 'error': 'Failed to initialize pipeline'}
        
        result = await pipeline.process_all_chambers(chamber_urls)
        return result
        
    finally:
        await pipeline.close()


if __name__ == "__main__":
    import sys
    
    async def main():
        chamber_urls = sys.argv[1:] if len(sys.argv) > 1 else None
        
        result = await run_chamber_pipeline(chamber_urls)
        
        if result['success']:
            print(f"✅ Pipeline completed successfully!")
            print(f"Processed: {result['successful_chambers']}/{result['total_chambers_attempted']} chambers")
            print(f"Businesses extracted: {result['total_businesses_extracted']}")
        else:
            print(f"❌ Pipeline failed: {result.get('error')}")
            sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Pipeline error: {e}")
        sys.exit(1)
