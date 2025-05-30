#!/usr/bin/env python3
# emergency_extraction.py - Simple fallback extraction for demo

import asyncio
from bs4 import BeautifulSoup
import re
from lead_gen_pipeline.crawler import AsyncWebCrawler
from lead_gen_pipeline.bulk_database import BulkDatabaseProcessor

async def emergency_extract_palo_alto():
    """Emergency fallback extraction for Palo Alto Chamber."""
    
    crawler = AsyncWebCrawler()
    db_processor = BulkDatabaseProcessor()
    
    try:
        # Get the directory page
        directory_url = "https://business.paloaltochamber.com/list"
        html_content, status_code, final_url = await crawler.fetch_page(directory_url)
        
        if status_code != 200:
            print(f"❌ Failed to fetch directory: {status_code}")
            return
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for business listings (adapt selectors based on actual page structure)
        businesses = []
        
        # Common selectors for business directories
        possible_selectors = [
            '.business-listing',
            '.member-listing', 
            '.directory-entry',
            '.listing-item',
            '[class*="business"]',
            '[class*="member"]',
            'article',
            '.card'
        ]
        
        listings = []
        for selector in possible_selectors:
            found = soup.select(selector)
            if found:
                listings = found
                print(f"✅ Found {len(found)} listings with selector: {selector}")
                break
        
        if not listings:
            # Fallback: look for any div with business-like text
            all_divs = soup.find_all('div')
            for div in all_divs:
                text = div.get_text().strip()
                if any(word in text.lower() for word in ['phone', 'website', 'email', 'address', 'contact']):
                    listings.append(div)
        
        print(f"Processing {len(listings)} potential business listings...")
        
        for listing in listings[:10]:  # Process first 10 for demo
            text = listing.get_text()
            
            # Extract basic info with regex
            name = None
            phone = None
            website = None
            email = None
            
            # Look for name (usually first heading or strong text)
            name_elem = listing.find(['h1', 'h2', 'h3', 'h4', 'strong', 'b'])
            if name_elem:
                name = name_elem.get_text().strip()
            
            # Extract phone numbers
            phone_match = re.search(r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})', text)
            if phone_match:
                phone = phone_match.group(1)
            
            # Extract emails
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
            if email_match:
                email = email_match.group(1)
            
            # Extract websites
            website_elem = listing.find('a', href=re.compile(r'^https?://'))
            if website_elem:
                website = website_elem['href']
            
            if name or phone or email:
                business = {
                    'company_name': name,
                    'website': website,
                    'phone_numbers': [phone] if phone else [],
                    'emails': [email] if email else [],
                    'addresses': [],
                    'social_media_links': {},
                    'industry_tags': [],
                    'scraped_from_url': directory_url,
                    'chamber_name': 'Palo Alto Chamber of Commerce',
                    'chamber_url': 'https://www.paloaltochamber.com'
                }
                businesses.append(business)
        
        # Save to database
        if businesses:
            await db_processor.bulk_insert_leads(businesses)
            print(f"✅ Emergency extraction completed! Saved {len(businesses)} businesses")
            
            # Show results
            for biz in businesses[:5]:
                print(f"- {biz['company_name']} | {biz['phone_numbers']} | {biz['website']}")
        else:
            print("❌ No businesses extracted")
            
    except Exception as e:
        print(f"❌ Emergency extraction failed: {e}")
    finally:
        await crawler.close()

if __name__ == "__main__":
    asyncio.run(emergency_extract_palo_alto())
