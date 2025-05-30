#!/usr/bin/env python3
# enhanced_chamber_extraction.py - Category-aware chamber processing

import asyncio
import json
from bs4 import BeautifulSoup
import re
from lead_gen_pipeline.crawler import AsyncWebCrawler
from lead_gen_pipeline.bulk_database import BulkDatabaseProcessor
from lead_gen_pipeline.llm_processor import create_llm_processor

async def enhanced_palo_alto_extraction():
    """Enhanced extraction that follows category links."""
    
    crawler = AsyncWebCrawler()
    db_processor = BulkDatabaseProcessor()
    llm_processor = create_llm_processor()
    await llm_processor.initialize()
    
    all_businesses = []
    
    try:
        # Step 1: Get the main directory page
        main_url = "https://business.paloaltochamber.com/list"
        print(f"🔍 Fetching main directory: {main_url}")
        
        html_content, status_code, final_url = await crawler.fetch_page(main_url)
        if status_code != 200:
            print(f"❌ Failed to fetch main directory: {status_code}")
            return
            
        # Step 2: Extract category links
        soup = BeautifulSoup(html_content, 'html.parser')
        category_links = []
        
        # Look for category links (they contain /ql/ in the URL)
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/ql/' in href and 'paloaltochamber.com' in href:
                if href not in category_links:
                    category_links.append(href)
                    
        print(f"✅ Found {len(category_links)} category links")
        for i, link in enumerate(category_links[:5], 1):  # Show first 5
            print(f"   {i}. {link}")
        if len(category_links) > 5:
            print(f"   ... and {len(category_links) - 5} more")
            
        # Step 3: Process each category (limit to first 5 for demo speed)
        for i, category_url in enumerate(category_links[:5], 1):
            print(f"\n🏢 Processing category {i}/{min(5, len(category_links))}: {category_url}")
            
            try:
                # Fetch category page
                cat_html, cat_status, cat_final_url = await crawler.fetch_page(category_url)
                if cat_status != 200:
                    print(f"   ❌ Failed to fetch category: {cat_status}")
                    continue
                    
                # Extract businesses using LLM
                businesses, next_page = await llm_processor.extract_business_listings(cat_html, category_url)
                
                if businesses:
                    print(f"   ✅ Extracted {len(businesses)} businesses")
                    
                    # Add chamber metadata
                    for business in businesses:
                        business['chamber_name'] = 'Palo Alto Chamber of Commerce'
                        business['chamber_url'] = 'https://www.paloaltochamber.com'
                        business['scraped_from_url'] = category_url
                        
                    all_businesses.extend(businesses)
                    
                    # Show sample
                    for biz in businesses[:2]:
                        print(f"      - {biz.get('name', 'N/A')} | {biz.get('phone', 'N/A')}")
                else:
                    print(f"   ⚠️  No businesses extracted from this category")
                    
            except Exception as e:
                print(f"   ❌ Error processing category: {e}")
                continue
                
            # Small delay between categories
            await asyncio.sleep(1)
            
        print(f"\n📊 EXTRACTION SUMMARY:")
        print(f"   Categories processed: {min(5, len(category_links))}")
        print(f"   Total businesses found: {len(all_businesses)}")
        print(f"   Estimated total if all categories: {len(all_businesses) * len(category_links) // min(5, len(category_links))}")
        
        # Step 4: Save to database
        if all_businesses:
            print(f"\n💾 Saving {len(all_businesses)} businesses to database...")
            
            # Convert to proper format
            formatted_businesses = []
            for biz in all_businesses:
                formatted_biz = {
                    'company_name': biz.get('name'),
                    'website': biz.get('website'),
                    'phone_numbers': [biz.get('phone')] if biz.get('phone') else [],
                    'emails': [biz.get('email')] if biz.get('email') else [],
                    'addresses': [biz.get('address')] if biz.get('address') else [],
                    'social_media_links': {},
                    'industry_tags': [biz.get('industry')] if biz.get('industry') else [],
                    'scraped_from_url': biz.get('source_url', biz.get('scraped_from_url')),
                    'chamber_name': biz.get('chamber_name'),
                    'chamber_url': biz.get('chamber_url')
                }
                if formatted_biz['company_name'] or formatted_biz['website']:
                    formatted_businesses.append(formatted_biz)
            
            # Use correct method name from BulkDatabaseProcessor
            chamber_info = {
                'name': 'Palo Alto Chamber of Commerce',
                'website': 'https://www.paloaltochamber.com'
            }
            
            stats = await db_processor.bulk_insert_businesses(formatted_businesses, chamber_info)
            print(f"✅ Saved {len(formatted_businesses)} businesses to database")
            
            # Show sample results
            print(f"\\n🎯 SAMPLE RESULTS:")
            for biz in formatted_businesses[:5]:
                print(f"   • {biz['company_name']} | {biz['phone_numbers']} | {biz['website']}")
                
        else:
            print("❌ No businesses to save")
            
    except Exception as e:
        print(f"❌ Enhanced extraction failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await crawler.close()
        await llm_processor.close()

if __name__ == "__main__":
    asyncio.run(enhanced_palo_alto_extraction())
