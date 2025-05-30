# lead_gen_pipeline/chamber_parser.py
# Chamber directory processing with LLM integration

import asyncio
from typing import Dict, List, Optional, Any, Set, Tuple
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
import time

try:
    from .utils import logger
    from .config import settings  
    from .crawler import AsyncWebCrawler
    from .llm_processor import get_llm_processor
    from .scraper import HTMLScraper
except ImportError:
    from lead_gen_pipeline.utils import logger
    from lead_gen_pipeline.config import settings
    from lead_gen_pipeline.crawler import AsyncWebCrawler
    from lead_gen_pipeline.llm_processor import get_llm_processor
    from lead_gen_pipeline.scraper import HTMLScraper

@dataclass
class ChamberDirectoryResult:
    """Result from processing a chamber directory."""
    chamber_url: str
    chamber_info: Dict[str, Any]
    business_listings: List[Dict[str, Any]]
    total_businesses_found: int
    pages_processed: int
    processing_time_seconds: float
    success: bool
    error_message: Optional[str] = None

class ChamberDirectoryParser:
    """Chamber of Commerce directory parser with LLM navigation."""
    
    def __init__(self):
        self.crawler: Optional[AsyncWebCrawler] = None
        self.llm_processor = get_llm_processor()
        self.processed_urls: Set[str] = set()
        self.max_pages_per_chamber = 50
        self.delay_between_requests = 2.0
        
    async def initialize(self) -> bool:
        """Initialize parser components."""
        try:
            self.crawler = AsyncWebCrawler()
            
            llm_success = await self.llm_processor.initialize()
            if not llm_success:
                logger.error("Failed to initialize LLM processor")
                return False
            
            logger.success("Chamber directory parser initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize chamber parser: {e}")
            return False
    
    async def _fetch_page_with_retry(self, url: str, max_retries: int = 3) -> Tuple[Optional[str], int, str]:
        """Fetch page with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                if not self.crawler:
                    raise RuntimeError("Crawler not initialized")
                
                html_content, status_code, final_url = await self.crawler.fetch_page(
                    url, use_playwright=True  # JS-heavy chamber sites need browser
                )
                
                if html_content and 200 <= status_code < 300:
                    return html_content, status_code, final_url
                
                logger.warning(f"Attempt {attempt + 1} failed for {url} (status: {status_code})")
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(self.delay_between_requests * (attempt + 1))
        
        logger.error(f"Failed to fetch {url} after {max_retries} attempts")
        return None, 0, url
    
    async def _extract_chamber_info(self, html_content: str, url: str) -> Dict[str, Any]:
        """Extract basic chamber information."""
        try:
            scraper = HTMLScraper(html_content, url)
            chamber_data = scraper.scrape()
            
            chamber_info = {
                'name': chamber_data.get('company_name') or 'Unknown Chamber',
                'website': chamber_data.get('website') or url,
                'phone_numbers': chamber_data.get('phone_numbers', []),
                'emails': chamber_data.get('emails', []),
                'addresses': chamber_data.get('addresses', []),
                'description': chamber_data.get('description'),
                'social_media_links': chamber_data.get('social_media_links', {}),
                'scraped_from_url': url
            }
            
            logger.info(f"Extracted chamber info: {chamber_info['name']}")
            return chamber_info
            
        except Exception as e:
            logger.error(f"Error extracting chamber info from {url}: {e}")
            return {
                'name': 'Unknown Chamber',
                'website': url,
                'scraped_from_url': url
            }
    
    async def _find_directory_pages(self, chamber_url: str) -> List[str]:
        """Find chamber business directory pages using LLM."""
        try:
            html_content, status_code, final_url = await self._fetch_page_with_retry(chamber_url)
            
            if not html_content:
                logger.error(f"Could not fetch chamber main page: {chamber_url}")
                return []
            
            directory_links = await self.llm_processor.find_directory_links(html_content, final_url)
            
            # Filter and validate links
            valid_links = []
            for link in directory_links:
                if link and link not in self.processed_urls:
                    parsed = urlparse(link)
                    if parsed.scheme and parsed.netloc:
                        valid_links.append(link)
            
            logger.info(f"Found {len(valid_links)} valid directory links")
            return valid_links
            
        except Exception as e:
            logger.error(f"Error finding directory pages: {e}")
            return []
    
    async def _extract_businesses_from_page(self, directory_url: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Extract business listings from directory page."""
        try:
            html_content, status_code, final_url = await self._fetch_page_with_retry(directory_url)
            
            if not html_content:
                logger.error(f"Could not fetch directory page: {directory_url}")
                return [], None
            
            businesses, next_page_url = await self.llm_processor.extract_business_listings(
                html_content, final_url
            )
            
            logger.info(f"Extracted {len(businesses)} businesses from {final_url}")
            return businesses, next_page_url
            
        except Exception as e:
            logger.error(f"Error extracting businesses from {directory_url}: {e}")
            return [], None
    
    async def _process_directory_pagination(self, initial_directory_url: str) -> List[Dict[str, Any]]:
        """Process directory with pagination support."""
        all_businesses = []
        current_url = initial_directory_url
        pages_processed = 0
        
        while current_url and pages_processed < self.max_pages_per_chamber:
            if current_url in self.processed_urls:
                logger.info(f"Skipping already processed URL: {current_url}")
                break
            
            self.processed_urls.add(current_url)
            pages_processed += 1
            
            logger.info(f"Processing directory page {pages_processed}: {current_url}")
            
            page_businesses, next_page_url = await self._extract_businesses_from_page(current_url)
            
            if page_businesses:
                all_businesses.extend(page_businesses)
                logger.info(f"Added {len(page_businesses)} businesses (total: {len(all_businesses)})")
            else:
                logger.warning(f"No businesses found on page: {current_url}")
            
            current_url = next_page_url
            
            if current_url:
                logger.info(f"Found next page: {current_url}")
                await asyncio.sleep(self.delay_between_requests)
            else:
                logger.info("No more pages found")
                break
        
        if pages_processed >= self.max_pages_per_chamber:
            logger.warning(f"Reached maximum pages limit ({self.max_pages_per_chamber})")
        
        logger.success(f"Completed directory: {len(all_businesses)} businesses from {pages_processed} pages")
        return all_businesses
    
    async def parse_chamber_directory(self, chamber_url: str) -> ChamberDirectoryResult:
        """Parse complete chamber directory."""
        start_time = time.time()
        
        logger.info(f"Starting chamber directory parsing: {chamber_url}")
        
        try:
            # Extract basic chamber information
            logger.info("Extracting chamber information...")
            chamber_html, _, chamber_final_url = await self._fetch_page_with_retry(chamber_url)
            
            if not chamber_html:
                return ChamberDirectoryResult(
                    chamber_url=chamber_url,
                    chamber_info={},
                    business_listings=[],
                    total_businesses_found=0,
                    pages_processed=0,
                    processing_time_seconds=time.time() - start_time,
                    success=False,
                    error_message="Could not fetch chamber main page"
                )
            
            chamber_info = await self._extract_chamber_info(chamber_html, chamber_final_url)
            
            # Find directory pages
            logger.info("Finding business directory pages...")
            directory_links = await self._find_directory_pages(chamber_final_url)
            
            if not directory_links:
                logger.warning("No directory links found, trying common patterns")
                # Fallback to common directory patterns
                fallback_links = [
                    urljoin(chamber_final_url, "/directory"),
                    urljoin(chamber_final_url, "/members"),
                    urljoin(chamber_final_url, "/business-directory"),
                    urljoin(chamber_final_url, "/member-directory"),
                    urljoin(chamber_final_url, "/businesses")
                ]
                directory_links = fallback_links
            
            # Extract businesses from all directory pages
            logger.info("Extracting business listings...")
            all_businesses = []
            total_pages_processed = 0
            
            for directory_url in directory_links:
                logger.info(f"Processing directory: {directory_url}")
                
                try:
                    directory_businesses = await self._process_directory_pagination(directory_url)
                    all_businesses.extend(directory_businesses)
                    
                    # Rough page count estimate
                    total_pages_processed += max(1, len(directory_businesses) // 20)
                    
                    logger.success(f"Completed directory {directory_url}: {len(directory_businesses)} businesses")
                    
                except Exception as e:
                    logger.error(f"Error processing directory {directory_url}: {e}")
                    continue
                
                await asyncio.sleep(self.delay_between_requests)
            
            # Deduplicate businesses
            logger.info("Deduplicating business listings...")
            unique_businesses = self._deduplicate_businesses(all_businesses)
            
            processing_time = time.time() - start_time
            
            result = ChamberDirectoryResult(
                chamber_url=chamber_url,
                chamber_info=chamber_info,
                business_listings=unique_businesses,
                total_businesses_found=len(unique_businesses),
                pages_processed=total_pages_processed,
                processing_time_seconds=processing_time,
                success=True
            )
            
            logger.success(f"Chamber parsing completed: {chamber_info.get('name', 'Unknown')}")
            logger.success(f"Results: {len(unique_businesses)} businesses from {total_pages_processed} pages in {processing_time:.1f}s")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Chamber parsing failed: {e}")
            
            return ChamberDirectoryResult(
                chamber_url=chamber_url,
                chamber_info={},
                business_listings=[],
                total_businesses_found=0,
                pages_processed=0,
                processing_time_seconds=processing_time,
                success=False,
                error_message=str(e)
            )
    
    def _deduplicate_businesses(self, businesses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate businesses based on name and website."""
        seen = set()
        unique_businesses = []
        
        for business in businesses:
            name = (business.get('name') or '').strip().lower()
            website = (business.get('website') or '').strip().lower()
            
            key = f"{name}|{website}"
            
            if key not in seen and (name or website):
                seen.add(key)
                unique_businesses.append(business)
        
        logger.info(f"Deduplicated {len(businesses)} -> {len(unique_businesses)} businesses")
        return unique_businesses
    
    async def parse_multiple_chambers(self, chamber_urls: List[str]) -> List[ChamberDirectoryResult]:
        """Parse multiple chambers with concurrency control."""
        results = []
        
        semaphore = asyncio.Semaphore(2)  # Max 2 concurrent chambers
        
        async def process_chamber_with_semaphore(url: str) -> ChamberDirectoryResult:
            async with semaphore:
                return await self.parse_chamber_directory(url)
        
        logger.info(f"Starting batch processing of {len(chamber_urls)} chambers")
        
        tasks = [process_chamber_with_semaphore(url) for url in chamber_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception processing chamber {chamber_urls[i]}: {result}")
                final_results.append(ChamberDirectoryResult(
                    chamber_url=chamber_urls[i],
                    chamber_info={},
                    business_listings=[],
                    total_businesses_found=0,
                    pages_processed=0,
                    processing_time_seconds=0,
                    success=False,
                    error_message=str(result)
                ))
            else:
                final_results.append(result)
        
        successful_chambers = sum(1 for r in final_results if r.success)
        total_businesses = sum(r.total_businesses_found for r in final_results)
        
        logger.success(f"Batch processing completed:")
        logger.success(f"   Successful chambers: {successful_chambers}/{len(chamber_urls)}")
        logger.success(f"   Total businesses extracted: {total_businesses}")
        
        return final_results
    
    async def close(self):
        """Clean up resources."""
        if self.crawler:
            await self.crawler.close()
        
        if self.llm_processor:
            await self.llm_processor.close()
        
        self.processed_urls.clear()
        logger.info("Chamber directory parser closed")
