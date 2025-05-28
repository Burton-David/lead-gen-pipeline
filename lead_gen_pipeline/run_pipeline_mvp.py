# run_pipeline_mvp.py
# Version: Gemini-2025-05-26 22:05 EDT

import asyncio
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Coroutine

try:
    from lead_gen_pipeline.config import settings
    from lead_gen_pipeline.utils import logger, setup_logger # setup_logger is called in utils itself
    from lead_gen_pipeline.crawler import AsyncWebCrawler
    from lead_gen_pipeline.scraper import HTMLScraper
    from lead_gen_pipeline.database import init_db, save_lead, get_async_session_local 
    from lead_gen_pipeline.models import Lead 
except ImportError:
    # This block is for cases where the script might be run in an environment
    # where the package structure is not immediately recognized (e.g. some IDEs or direct execution)
    # For robust package execution, prefer running as a module: python -m lead_gen_pipeline.run_pipeline_mvp
    print("Attempting fallback imports for run_pipeline_mvp.py. Consider running as a module.", file=sys.stderr)
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent)) # Add project root to path
    from lead_gen_pipeline.config import settings
    from lead_gen_pipeline.utils import logger, setup_logger
    from lead_gen_pipeline.crawler import AsyncWebCrawler
    from lead_gen_pipeline.scraper import HTMLScraper
    from lead_gen_pipeline.database import init_db, save_lead, get_async_session_local
    from lead_gen_pipeline.models import Lead


async def process_single_url(
    url: str,
    crawler: AsyncWebCrawler,
    pipeline_semaphore: asyncio.Semaphore
) -> Optional[Dict[str, Any]]:
    """
    Processes a single URL: crawls, scrapes, and prepares data for saving.
    Returns scraped data dictionary or None if processing fails.
    """
    async with pipeline_semaphore: # Limit overall pipeline concurrency
        logger.info(f"[PROCESSOR] Starting processing for URL: {url}")
        try:
            # Determine if Playwright should be used (can be based on URL patterns or global setting)
            # For MVP, using global setting.
            use_playwright_for_url = settings.crawler.USE_PLAYWRIGHT_BY_DEFAULT
            
            html_content, status_code, final_url = await crawler.fetch_page(
                url, use_playwright=use_playwright_for_url
            )

            if not html_content or not (200 <= status_code < 300):
                logger.error(
                    f"[PROCESSOR] Failed to fetch content from {url} (status: {status_code}). Final URL: {final_url}. Skipping."
                )
                return None # Indicate failure for this URL

            logger.info(f"[PROCESSOR] Successfully fetched {final_url} (status: {status_code}). Proceeding to scrape.")
            
            scraper = HTMLScraper(html_content=html_content, source_url=final_url)
            scraped_data = scraper.scrape() # This returns a Dict[str, Any]

            if not scraped_data or not any(scraped_data.get(key) for key in ["company_name", "emails", "phone_numbers"]):
                logger.warning(f"[PROCESSOR] Minimal or no data scraped from {final_url}. Skipping save for this URL.")
                # We can add the original seed URL for tracking even if other data is sparse
                # scraped_data["original_seed_url"] = url # Add if you want to save even sparse entries
                return None # Or return sparse data if you decide to save it

            # Add original seed URL for reference, as final_url might be different due to redirects
            scraped_data["original_seed_url"] = url 
            logger.success(f"[PROCESSOR] Successfully scraped data from {final_url} (Original: {url}).")
            return scraped_data

        except Exception as e:
            # Log detailed error including stack trace for debugging
            logger.error(f"[PROCESSOR] Critical error processing URL {url}: {type(e).__name__} - {e}", exc_info=True)
            return None # Indicate failure for this URL

async def main_pipeline():
    """
    Main orchestration function for the MVP pipeline.
    Reads seed URLs, crawls, scrapes, and saves lead data.
    """
    logger.info("--- B2B LEAD GENERATION PIPELINE MVP START ---")
    logger.info(f"[CONFIG] Max pipeline concurrency: {settings.MAX_PIPELINE_CONCURRENCY}")
    logger.info(f"[CONFIG] Input CSV: {settings.INPUT_URLS_CSV}")
    logger.info(f"[CONFIG] Database URL: {settings.database.DATABASE_URL}")
    logger.info(f"[CONFIG] Respect robots.txt: {settings.crawler.RESPECT_ROBOTS_TXT}")
    logger.info(f"[CONFIG] Default Playwright Use: {settings.crawler.USE_PLAYWRIGHT_BY_DEFAULT}")

    # Initialize database (create tables if they don't exist)
    try:
        await init_db() 
        logger.info("[DB_INIT] Database initialized successfully (tables checked/created).")
    except Exception as e:
        logger.critical(f"[DB_INIT] CRITICAL: Failed to initialize database: {e}. Pipeline cannot continue.", exc_info=True)
        return # Exit if DB init fails

    # Load seed URLs from CSV
    seed_urls: List[str] = []
    try:
        if not settings.INPUT_URLS_CSV.exists():
            logger.error(f"[LOAD_URLS] Input CSV file not found: {settings.INPUT_URLS_CSV}")
            logger.info("--- PIPELINE END (Error) ---")
            return

        with open(settings.INPUT_URLS_CSV, mode='r', encoding='utf-8-sig') as csvfile: # utf-8-sig for potential BOM
            reader = csv.DictReader(csvfile)
            if 'url' not in (reader.fieldnames or []): 
                logger.error(f"[LOAD_URLS] 'url' column not found in CSV header of {settings.INPUT_URLS_CSV}.")
                logger.info("--- PIPELINE END (Error) ---")
                return
            for row_number, row in enumerate(reader, 1):
                url = row.get('url', '').strip()
                if url:
                    if url.startswith("http://") or url.startswith("https://"):
                        seed_urls.append(url)
                    else:
                        logger.warning(f"[LOAD_URLS] Row {row_number}: Invalid URL format (must start with http/https): '{url}'. Skipping.")
                else:
                    logger.warning(f"[LOAD_URLS] Row {row_number}: Empty URL found. Skipping.")
        
        if not seed_urls:
            logger.warning("[LOAD_URLS] No valid seed URLs found in the input CSV file.")
            logger.info("--- PIPELINE END (No URLs) ---")
            return
        logger.info(f"[LOAD_URLS] Loaded {len(seed_urls)} valid seed URLs for processing.")

    except Exception as e:
        logger.error(f"[LOAD_URLS] Failed to read or parse seed URLs from {settings.INPUT_URLS_CSV}: {e}", exc_info=True)
        logger.info("--- PIPELINE END (Error) ---")
        return

    crawler = AsyncWebCrawler() # Initialize crawler
    # Semaphore to limit the number of concurrent URL processing tasks
    pipeline_semaphore = asyncio.Semaphore(settings.MAX_PIPELINE_CONCURRENCY)
    
    processing_tasks: List[Coroutine[Any, Any, Optional[Dict[str, Any]]]] = []
    for url in seed_urls:
        processing_tasks.append(process_single_url(url, crawler, pipeline_semaphore))
    
    logger.info(f"[DISPATCH] Dispatching {len(processing_tasks)} URL processing tasks...")
    # Execute all processing tasks concurrently, respecting the semaphore
    # return_exceptions=False means if a task raises an exception not caught internally, gather will stop.
    # We catch exceptions within process_single_url to allow other tasks to continue.
    scraped_results: List[Optional[Dict[str, Any]]] = await asyncio.gather(*processing_tasks, return_exceptions=False)
    logger.info("[DISPATCH] All URL processing tasks (crawl & scrape) have completed their initial phase.")

    # Save successfully scraped data to the database
    saved_count = 0
    failed_to_save_count = 0
    
    logger.info("[DB_SAVE] Starting database save operations for scraped results...")
    
    # Get the session factory for creating sessions
    session_factory = get_async_session_local() 

    # Use a single session for this batch of save operations for efficiency
    async with session_factory() as db_session: 
        logger.debug(f"[DB_SAVE] Opened DB session for batch save. Bound to: {db_session.bind}")
        for i, lead_data_to_save in enumerate(scraped_results):
            if lead_data_to_save: # Check if data was successfully scraped
                original_url_log = lead_data_to_save.get("original_seed_url", f"Result from Processed Task {i+1}")
                logger.debug(f"[DB_SAVE] Preparing to save lead data from: {original_url_log}")
                
                # Ensure no unexpected keys are passed to the Lead model if it's strict
                # This step can be enhanced with Pydantic validation of scraped_data against a LeadData model
                valid_lead_model_keys = {column.name for column in Lead.__table__.columns}
                filtered_lead_data = {k: v for k, v in lead_data_to_save.items() if k in valid_lead_model_keys}
                
                saved_lead_model: Optional[Lead] = await save_lead(filtered_lead_data, db_session=db_session)
                if saved_lead_model and saved_lead_model.id is not None:
                    saved_count += 1
                else:
                    failed_to_save_count += 1
                    logger.error(f"[DB_SAVE] Failed to save lead data from: {original_url_log}")
            else:
                # This means process_single_url returned None, error already logged there.
                logger.debug(f"[DB_SAVE] Skipping save for URL that failed processing (Result #{i+1}).")
        
        # Commit all changes made in this session if any leads were successfully added
        if saved_count > 0 or (db_session.new or db_session.dirty or db_session.deleted): # Check if there's anything to commit
            logger.info(f"[DB_COMMIT] Attempting to commit {saved_count} new/updated leads to the database...")
            try:
                await db_session.commit()
                logger.success(f"[DB_COMMIT] Batch commit successful. {saved_count} leads processed for this commit.")
            except Exception as e:
                logger.error(f"[DB_COMMIT] Error during batch commit: {e}. Attempting rollback.", exc_info=True)
                try:
                    await db_session.rollback()
                    logger.info("[DB_ROLLBACK] Rollback successful after commit error.")
                except Exception as rb_e: # Error during rollback itself
                    logger.critical(f"[DB_ROLLBACK] CRITICAL: Error during rollback: {rb_e}", exc_info=True)
                # Update counts to reflect commit failure
                failed_to_save_count += saved_count 
                saved_count = 0 
        elif failed_to_save_count > 0 :
             logger.warning(f"[DB_COMMIT] No leads were successfully prepared for commit in this batch. {failed_to_save_count} failed prior to commit stage.")
        else:
            logger.info("[DB_COMMIT] No new leads or changes to commit in this batch.")
        
    logger.info("[DB_SAVE] Database save operations batch complete.")

    # Final summary
    logger.info(f"--- PIPELINE SUMMARY ---")
    total_processed_urls = len(scraped_results)
    logger.info(f"Total URLs attempted for processing: {total_processed_urls}")
    logger.info(f"Successfully saved new leads to DB in this run: {saved_count}")
    # Number of URLs that did not result in a saved lead (either scrape failed or save failed)
    total_failed_or_skipped = total_processed_urls - saved_count
    logger.info(f"URLs that did not result in a saved lead (failed scrape/save or no data): {total_failed_or_skipped}")
    
    # Clean up crawler resources (e.g., close Playwright browser)
    try:
        await crawler.close()
        logger.info("[CLEANUP] Crawler resources closed successfully.")
    except Exception as e:
        logger.error(f"[CLEANUP] Error closing crawler resources: {e}", exc_info=True)

    logger.info("--- PIPELINE END ---")


if __name__ == "__main__":
    # Ensure logger is set up (utils.py does this on import, but good for clarity)
    # setup_logger() # Already called at module level in utils

    try:
        asyncio.run(main_pipeline())
    except KeyboardInterrupt:
        logger.warning("Pipeline run interrupted by user (KeyboardInterrupt). Shutting down...")
    except Exception as e: # Catch-all for any unhandled exceptions from asyncio.run or main_pipeline itself
        logger.critical(f"CRITICAL: Unhandled exception during pipeline execution: {e}", exc_info=True)
    finally:
        logger.info("Pipeline execution finished or terminated.")
