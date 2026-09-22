"""Single-page pipeline: crawl seed URLs, scrape each page, and save leads."""

import asyncio
import csv
from collections.abc import Coroutine
from typing import Any

from lead_gen_pipeline.config import settings
from lead_gen_pipeline.crawler import AsyncWebCrawler
from lead_gen_pipeline.database import get_async_session_local, init_db, save_lead
from lead_gen_pipeline.models import Lead
from lead_gen_pipeline.scraper import HTMLScraper
from lead_gen_pipeline.utils import logger

# Fields worth saving a lead for; a page with none of these is treated as empty.
_SIGNAL_FIELDS = ("company_name", "emails", "phone_numbers")


async def process_single_url(
    url: str,
    crawler: AsyncWebCrawler,
    pipeline_semaphore: asyncio.Semaphore,
) -> dict[str, Any] | None:
    """Crawl and scrape a single URL, returning lead data or None on failure."""
    async with pipeline_semaphore:
        logger.info(f"Processing {url}")
        try:
            html_content, status_code, final_url = await crawler.fetch_page(
                url, use_playwright=settings.crawler.USE_PLAYWRIGHT_BY_DEFAULT
            )

            if not html_content or not (200 <= status_code < 300):
                logger.error(f"Failed to fetch {url} (status {status_code})")
                return None

            scraped = HTMLScraper(
                html_content=html_content, source_url=final_url
            ).scrape()
            if not any(scraped.get(field) for field in _SIGNAL_FIELDS):
                logger.warning(f"No usable data scraped from {final_url}; skipping")
                return None

            scraped["original_seed_url"] = url
            logger.success(f"Scraped {final_url}")
            return scraped
        except Exception as e:
            logger.error(f"Error processing {url}: {type(e).__name__} - {e}")
            return None


def _load_seed_urls() -> list[str]:
    """Read and validate seed URLs from the configured input CSV."""
    if not settings.INPUT_URLS_CSV.exists():
        logger.error(f"Input CSV not found: {settings.INPUT_URLS_CSV}")
        return []

    seed_urls: list[str] = []
    with open(settings.INPUT_URLS_CSV, encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        if "url" not in (reader.fieldnames or []):
            logger.error(f"'url' column missing in {settings.INPUT_URLS_CSV}")
            return []
        for row_number, row in enumerate(reader, 1):
            url = (row.get("url") or "").strip()
            if not url:
                logger.warning(f"Row {row_number}: empty URL; skipping")
            elif url.startswith(("http://", "https://")):
                seed_urls.append(url)
            else:
                logger.warning(f"Row {row_number}: invalid URL '{url}'; skipping")
    return seed_urls


async def main_pipeline() -> None:
    """Run the single-page pipeline end to end."""
    logger.info("Pipeline run started")
    logger.info(f"Input CSV: {settings.INPUT_URLS_CSV}")
    logger.info(f"Database: {settings.database.DATABASE_URL}")

    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.critical(f"Database init failed: {e}. Aborting.")
        return

    seed_urls = _load_seed_urls()
    if not seed_urls:
        logger.warning("No valid seed URLs; nothing to do")
        logger.info("Pipeline run finished")
        return
    logger.info(f"Loaded {len(seed_urls)} seed URLs")

    crawler = AsyncWebCrawler()
    semaphore = asyncio.Semaphore(settings.MAX_PIPELINE_CONCURRENCY)
    tasks: list[Coroutine[Any, Any, dict[str, Any] | None]] = [
        process_single_url(url, crawler, semaphore) for url in seed_urls
    ]
    results = await asyncio.gather(*tasks)

    saved_count = 0
    valid_columns = {column.name for column in Lead.__table__.columns}
    session_factory = get_async_session_local()
    async with session_factory() as session:
        for lead_data in results:
            if not lead_data:
                continue
            filtered = {k: v for k, v in lead_data.items() if k in valid_columns}
            saved = await save_lead(filtered, db_session=session)
            if saved is not None and saved.id is not None:
                saved_count += 1
                logger.success(f"Saved lead id {saved.id}")
            else:
                logger.error(
                    f"Failed to save lead from {lead_data.get('original_seed_url')}"
                )
        if saved_count:
            await session.commit()
            logger.success(f"Committed {saved_count} leads")

    logger.info(f"Saved {saved_count} of {len(results)} processed URLs")
    try:
        await crawler.close()
    except Exception as e:
        logger.error(f"Error closing crawler: {e}")
    logger.info("Pipeline run finished")


if __name__ == "__main__":
    try:
        asyncio.run(main_pipeline())
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
