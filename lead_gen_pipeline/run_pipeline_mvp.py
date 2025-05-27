# run_pipeline_mvp.py
# Version: Gemini-2025-05-26 21:03 EDT

import asyncio
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional

from lead_gen_pipeline.config import settings
from lead_gen_pipeline.utils import logger, setup_logger
from lead_gen_pipeline.crawler import AsyncWebCrawler
from lead_gen_pipeline.scraper import HTMLScraper
# Import the factory function, not AsyncSessionLocal directly
from lead_gen_pipeline.database import init_db, save_lead, get_async_session_local 
from lead_gen_pipeline.models import Lead 

setup_logger()

async def process_single_url(
    url: str,
    crawler: AsyncWebCrawler,
    pipeline_semaphore: asyncio.Semaphore
) -> Optional[Dict[str, Any]]:
    """
    Processes a single URL: crawls, scrapes, and prepares data for saving.
    """
    async with pipeline_semaphore:
        logger.info(f"[PROCESSOR] Starting for URL: {url}")
        try:
            use_playwright_for_url = settings.crawler.USE_PLAYWRIGHT_BY_DEFAULT
            html_content, status_code, final_url = await crawler.fetch_page(
                url, use_playwright=use_playwright_for_url
            )

            if not html_content or not (200 <= status_code < 300):
                logger.error(
                    f"[PROCESSOR] Failed to fetch {url} (status: {status_code}). Final URL: {final_url}. Skipping."
                )
                return None

            logger.info(f"[PROCESSOR] Fetched {final_url} (status: {status_code}). Scraping...")
            scraper = HTMLScraper(html_content=html_content, source_url=final_url)
            scraped_data = scraper.scrape()

            if not scraped_data:
                logger.warning(f"[PROCESSOR] No data scraped from {final_url}. Skipping save.")
                return None
            
            scraped_data["original_seed_url"] = url 
            logger.success(f"[PROCESSOR] Scraped data from {final_url}.")
            return scraped_data

        except Exception as e:
            logger.error(f"[PROCESSOR] Exception for URL {url}: {e}", exc_info=True)
            return None

async def main_pipeline():
    """
    Main orchestration function for the MVP pipeline.
    """
    logger.info("--- PIPELINE START ---")
    logger.info(f"[CONFIG] Max concurrency: {settings.MAX_PIPELINE_CONCURRENCY}")
    logger.info(f"[CONFIG] Input CSV: {settings.INPUT_URLS_CSV}")
    logger.info(f"[CONFIG] Database URL (from settings): {settings.database.DATABASE_URL}")

    try:
        await init_db() 
        logger.info("[DB_INIT] Database initialized successfully.")
    except Exception as e:
        logger.critical(f"[DB_INIT] Failed to initialize database: {e}. Pipeline cannot continue.", exc_info=True)
        return

    seed_urls: List[str] = []
    try:
        if not settings.INPUT_URLS_CSV.exists():
            logger.error(f"[LOAD_URLS] Input CSV not found: {settings.INPUT_URLS_CSV}")
            return

        with open(settings.INPUT_URLS_CSV, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            if 'url' not in (reader.fieldnames or []): 
                logger.error(f"[LOAD_URLS] 'url' column not found in {settings.INPUT_URLS_CSV}.")
                return
            for row in reader:
                url = row.get('url', '').strip()
                if url:
                    seed_urls.append(url)
        
        if not seed_urls:
            logger.warning("[LOAD_URLS] No seed URLs found in CSV.")
            return
        logger.info(f"[LOAD_URLS] Loaded {len(seed_urls)} seed URLs.")

    except Exception as e:
        logger.error(f"[LOAD_URLS] Failed to read/parse seed URLs: {e}", exc_info=True)
        return

    crawler = AsyncWebCrawler()
    pipeline_semaphore = asyncio.Semaphore(settings.MAX_PIPELINE_CONCURRENCY)
    tasks = [process_single_url(url, crawler, pipeline_semaphore) for url in seed_urls]
    
    logger.info(f"[DISPATCH] Dispatching {len(tasks)} URL processing tasks...")
    results: List[Optional[Dict[str, Any]]] = await asyncio.gather(*tasks, return_exceptions=False)
    logger.info("[DISPATCH] All URL processing tasks completed initial phase (crawl & scrape).")

    saved_count = 0
    failed_to_save_count = 0
    
    logger.info("[DB_SAVE] Starting database save operations...")
    
    # Get the session factory from database.py
    # This factory will use the (potentially patched in tests) engine
    session_factory = get_async_session_local() 

    async with session_factory() as db_session: # Use the factory to create a session
        logger.debug(f"[DB_SAVE] Opened DB session using factory. Bound to: {db_session.bind}")
        for i, lead_data_to_save in enumerate(results):
            if lead_data_to_save:
                original_url_log = lead_data_to_save.get("original_seed_url", f"Result {i+1}")
                logger.debug(f"[DB_SAVE] Preparing to save lead for: {original_url_log}")
                saved_lead: Optional[Lead] = await save_lead(lead_data_to_save, db_session=db_session)
                if saved_lead:
                    saved_count +=1
                else:
                    failed_to_save_count += 1
            else:
                logger.warning(f"[DB_SAVE] Skipping save for URL that failed earlier. Processed result #{i+1}")
        
        if saved_count > 0:
            logger.info(f"[DB_COMMIT] Attempting batch commit for {saved_count} leads...")
            try:
                await db_session.commit()
                logger.success(f"[DB_COMMIT] Batch commit successful for {saved_count} leads.")
            except Exception as e:
                logger.error(f"[DB_COMMIT] Error during batch commit: {e}. Attempting rollback.", exc_info=True)
                try:
                    await db_session.rollback()
                    logger.info("[DB_ROLLBACK] Rollback successful after commit error.")
                except Exception as rb_e:
                    logger.error(f"[DB_ROLLBACK] Error during rollback: {rb_e}", exc_info=True)
                failed_to_save_count += saved_count 
                saved_count = 0 
        elif failed_to_save_count > 0 :
             logger.warning(f"[DB_COMMIT] No leads successfully prepared for commit. {failed_to_save_count} failed prior.")
        else:
            logger.info("[DB_COMMIT] No new leads to commit.")
        
        # Session is automatically closed by the async context manager
        logger.info("[DB_SAVE] Pipeline database session operations complete.")


    logger.info(f"--- PIPELINE SUMMARY ---")
    logger.info(f"Total URLs processed (crawl/scrape attempt): {len(results)}")
    logger.info(f"Successfully saved leads to DB: {saved_count}")
    total_failed_scrape_or_save = len(results) - saved_count
    logger.info(f"Total failed (scrape or DB save): {total_failed_scrape_or_save}")
    
    try:
        await crawler.close()
        logger.info("[CLEANUP] Crawler resources closed.")
    except Exception as e:
        logger.error(f"[CLEANUP] Error closing crawler resources: {e}", exc_info=True)

    logger.info("--- PIPELINE END ---")


if __name__ == "__main__":
    try:
        asyncio.run(main_pipeline())
    except KeyboardInterrupt:
        logger.warning("Pipeline run interrupted by user (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"Critical unhandled exception in pipeline execution: {e}", exc_info=True)
