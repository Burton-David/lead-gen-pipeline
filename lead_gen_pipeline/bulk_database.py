# lead_gen_pipeline/bulk_database.py
# High-performance database operations for large-scale business data

import asyncio
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
import time
from datetime import datetime
import hashlib

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy import text, select, and_, or_
from sqlalchemy.exc import IntegrityError

try:
    from .database import get_async_session_local, get_engine
    from .models import Lead, Base
    from .utils import logger
    from .config import settings
except ImportError:
    from lead_gen_pipeline.database import get_async_session_local, get_engine
    from lead_gen_pipeline.models import Lead, Base
    from lead_gen_pipeline.utils import logger
    from lead_gen_pipeline.config import settings

@dataclass
class BulkInsertStats:
    """Statistics from bulk insert operations."""
    total_attempted: int
    successful_inserts: int
    successful_updates: int
    duplicates_skipped: int
    errors: int
    processing_time_seconds: float
    records_per_second: float

class BulkDatabaseProcessor:
    """High-performance database processor for chamber directory data."""
    
    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size
        self.session_factory = get_async_session_local()
        self.engine = get_engine()
        
        self.processed_hashes: Set[str] = set()
        self.total_processed = 0
        self.start_time = time.time()
        
        logger.info(f"BulkDatabaseProcessor initialized with batch_size={batch_size}")
    
    def _create_business_hash(self, business_data: Dict[str, Any]) -> str:
        """Create hash for business deduplication."""
        website = (business_data.get('website') or '').strip().lower()
        company_name = (business_data.get('company_name') or business_data.get('name') or '').strip().lower()
        
        hash_input = f"{website}|{company_name}"
        return hashlib.md5(hash_input.encode('utf-8')).hexdigest()
    
    def _normalize_business_data(self, business_data: Dict[str, Any], chamber_info: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize business data for database insertion."""
        company_name = (
            business_data.get('name') or 
            business_data.get('company_name') or 
            business_data.get('business_name')
        )
        
        website = business_data.get('website')
        if website and not website.startswith(('http://', 'https://')):
            website = f"https://{website}"
        
        # Normalize collections
        phone_numbers = [business_data['phone']] if business_data.get('phone') else None
        emails = [business_data['email']] if business_data.get('email') else None
        addresses = [business_data['address']] if business_data.get('address') else None
        industry_tags = [business_data['industry']] if business_data.get('industry') else None
        
        normalized = {
            'company_name': company_name,
            'website': website,
            'scraped_from_url': business_data.get('source_url') or chamber_info.get('website'),
            'canonical_url': website,
            'description': business_data.get('description'),
            'phone_numbers': phone_numbers,
            'emails': emails,
            'addresses': addresses,
            'social_media_links': business_data.get('social_media_links'),
            'industry_tags': industry_tags,
            'chamber_name': chamber_info.get('name'),
            'chamber_url': chamber_info.get('website')
        }
        
        # Remove None values
        return {k: v for k, v in normalized.items() if v is not None}
    
    async def _create_indexes_if_needed(self):
        """Create performance indexes."""
        try:
            async with self.engine.begin() as conn:
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_leads_company_name_lower ON leads (LOWER(company_name))",
                    "CREATE INDEX IF NOT EXISTS idx_leads_website_lower ON leads (LOWER(website))",
                    "CREATE INDEX IF NOT EXISTS idx_leads_scraped_from_url ON leads (scraped_from_url)",
                    "CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads (created_at)",
                    "CREATE INDEX IF NOT EXISTS idx_leads_emails_json ON leads (json_extract(emails, '$[0]'))",
                    "CREATE INDEX IF NOT EXISTS idx_leads_phone_json ON leads (json_extract(phone_numbers, '$[0]'))"
                ]
                
                for index_sql in indexes:
                    try:
                        await conn.execute(text(index_sql))
                    except Exception:
                        pass  # Index may already exist
                
                logger.info("Database indexes verified")
                
        except Exception as e:
            logger.warning(f"Could not create indexes: {e}")
    
    async def bulk_insert_businesses(
        self, 
        businesses: List[Dict[str, Any]], 
        chamber_info: Dict[str, Any],
        update_existing: bool = True
    ) -> BulkInsertStats:
        """Bulk insert businesses with deduplication."""
        start_time = time.time()
        
        if not businesses:
            return BulkInsertStats(0, 0, 0, 0, 0, 0, 0)
        
        logger.info(f"Starting bulk insert of {len(businesses)} businesses")
        
        await self._create_indexes_if_needed()
        
        # Normalize and deduplicate
        normalized_businesses = []
        duplicates_skipped = 0
        
        for business_data in businesses:
            try:
                normalized = self._normalize_business_data(business_data, chamber_info)
                
                if not normalized.get('company_name') and not normalized.get('website'):
                    continue
                
                business_hash = self._create_business_hash(normalized)
                if business_hash in self.processed_hashes:
                    duplicates_skipped += 1
                    continue
                
                self.processed_hashes.add(business_hash)
                normalized_businesses.append(normalized)
                
            except Exception as e:
                logger.error(f"Error normalizing business data: {e}")
                continue
        
        if not normalized_businesses:
            logger.warning("No valid businesses to insert after normalization")
            return BulkInsertStats(
                len(businesses), 0, 0, duplicates_skipped, 
                len(businesses) - duplicates_skipped, 0, 0
            )
        
        # Process in batches
        successful_inserts = 0
        successful_updates = 0
        errors = 0
        
        async with self.session_factory() as session:
            for i in range(0, len(normalized_businesses), self.batch_size):
                batch = normalized_businesses[i:i + self.batch_size]
                batch_num = (i // self.batch_size) + 1
                
                logger.info(f"Processing batch {batch_num} ({len(batch)} records)")
                
                try:
                    batch_inserts, batch_updates, batch_errors = await self._process_batch(
                        session, batch, update_existing
                    )
                    
                    successful_inserts += batch_inserts
                    successful_updates += batch_updates
                    errors += batch_errors
                    
                    await session.commit()
                    
                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {e}")
                    await session.rollback()
                    errors += len(batch)
                    continue
        
        processing_time = time.time() - start_time
        total_processed = successful_inserts + successful_updates
        records_per_second = total_processed / processing_time if processing_time > 0 else 0
        
        stats = BulkInsertStats(
            total_attempted=len(businesses),
            successful_inserts=successful_inserts,
            successful_updates=successful_updates,
            duplicates_skipped=duplicates_skipped,
            errors=errors,
            processing_time_seconds=processing_time,
            records_per_second=records_per_second
        )
        
        logger.success(f"Bulk insert completed: {successful_inserts} inserts, {successful_updates} updates")
        logger.success(f"Processing rate: {records_per_second:.1f} records/second")
        
        return stats
    
    async def _process_batch(
        self, 
        session: AsyncSession, 
        batch: List[Dict[str, Any]], 
        update_existing: bool
    ) -> Tuple[int, int, int]:
        """Process a single batch of business records."""
        inserts = 0
        updates = 0
        errors = 0
        
        for business_data in batch:
            try:
                # Check for existing record
                existing_query = select(Lead).where(
                    or_(
                        and_(
                            Lead.website.isnot(None),
                            Lead.website == business_data.get('website')
                        ),
                        and_(
                            Lead.company_name.isnot(None),
                            Lead.company_name == business_data.get('company_name')
                        )
                    )
                ).limit(1)
                
                result = await session.execute(existing_query)
                existing_lead = result.scalar_one_or_none()
                
                if existing_lead and update_existing:
                    # Update existing record
                    for key, value in business_data.items():
                        if hasattr(existing_lead, key) and value is not None:
                            setattr(existing_lead, key, value)
                    
                    existing_lead.updated_at = datetime.utcnow()
                    updates += 1
                    
                elif not existing_lead:
                    # Insert new record
                    new_lead = Lead(**business_data)
                    session.add(new_lead)
                    inserts += 1
                
            except Exception as e:
                logger.error(f"Error processing record: {e}")
                errors += 1
                continue
        
        return inserts, updates, errors
    
    async def bulk_insert_chamber_results(
        self, 
        chamber_results: List[Any],
        update_existing: bool = True
    ) -> Dict[str, BulkInsertStats]:
        """Bulk insert results from multiple chambers."""
        all_stats = {}
        
        logger.info(f"Starting bulk insert of {len(chamber_results)} chamber results")
        
        for result in chamber_results:
            if not result.success:
                continue
            
            try:
                stats = await self.bulk_insert_businesses(
                    result.business_listings,
                    result.chamber_info,
                    update_existing
                )
                
                all_stats[result.chamber_url] = stats
                self.total_processed += stats.successful_inserts + stats.successful_updates
                
            except Exception as e:
                logger.error(f"Error processing chamber result: {e}")
                continue
        
        # Summary
        total_inserts = sum(stats.successful_inserts for stats in all_stats.values())
        total_updates = sum(stats.successful_updates for stats in all_stats.values())
        total_errors = sum(stats.errors for stats in all_stats.values())
        
        logger.success(f"Bulk chamber processing completed:")
        logger.success(f"   Chambers processed: {len(all_stats)}")
        logger.success(f"   Businesses inserted: {total_inserts}")
        logger.success(f"   Businesses updated: {total_updates}")
        logger.success(f"   Errors: {total_errors}")
        
        return all_stats
    
    async def get_database_statistics(self) -> Dict[str, Any]:
        """Get comprehensive database statistics."""
        try:
            async with self.session_factory() as session:
                result = await session.execute(select(Lead))
                all_leads = result.scalars().all()
                total_count = len(all_leads)
                
                if total_count == 0:
                    return {
                        'total_leads': 0,
                        'leads_with_emails': 0,
                        'leads_with_phones': 0,
                        'leads_with_websites': 0,
                        'unique_domains': 0,
                        'processing_rate': 0
                    }
                
                # Calculate stats
                leads_with_emails = sum(1 for lead in all_leads if lead.emails)
                leads_with_phones = sum(1 for lead in all_leads if lead.phone_numbers)
                leads_with_websites = sum(1 for lead in all_leads if lead.website)
                
                # Unique domains
                domains = set()
                for lead in all_leads:
                    if lead.website:
                        try:
                            from urllib.parse import urlparse
                            domain = urlparse(lead.website).netloc
                            if domain:
                                domains.add(domain)
                        except:
                            continue
                
                elapsed_time = time.time() - self.start_time
                processing_rate = self.total_processed / elapsed_time if elapsed_time > 0 else 0
                
                stats = {
                    'total_leads': total_count,
                    'leads_with_emails': leads_with_emails,
                    'leads_with_phones': leads_with_phones,
                    'leads_with_websites': leads_with_websites,
                    'leads_with_emails_pct': (leads_with_emails / total_count * 100) if total_count > 0 else 0,
                    'leads_with_phones_pct': (leads_with_phones / total_count * 100) if total_count > 0 else 0,
                    'leads_with_websites_pct': (leads_with_websites / total_count * 100) if total_count > 0 else 0,
                    'unique_domains': len(domains),
                    'total_processed_this_session': self.total_processed,
                    'processing_rate_per_second': processing_rate,
                    'elapsed_time_seconds': elapsed_time
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting database statistics: {e}")
            return {}
    
    async def optimize_database(self):
        """Apply database optimizations."""
        try:
            async with self.engine.begin() as conn:
                if 'sqlite' in str(self.engine.url):
                    optimizations = [
                        "PRAGMA journal_mode=WAL",
                        "PRAGMA synchronous=NORMAL", 
                        "PRAGMA cache_size=10000",
                        "PRAGMA temp_store=memory",
                        "PRAGMA mmap_size=268435456",  # 256MB
                        "ANALYZE"
                    ]
                    
                    for pragma in optimizations:
                        try:
                            await conn.execute(text(pragma))
                        except Exception:
                            pass
                
                logger.info("Database optimizations applied")
                
        except Exception as e:
            logger.warning(f"Could not apply database optimizations: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for current session."""
        elapsed_time = time.time() - self.start_time
        processing_rate = self.total_processed / elapsed_time if elapsed_time > 0 else 0
        
        return {
            'total_processed': self.total_processed,
            'elapsed_time_seconds': elapsed_time,
            'processing_rate_per_second': processing_rate,
            'unique_hashes_tracked': len(self.processed_hashes)
        }
