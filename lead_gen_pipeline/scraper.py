# lead_gen_pipeline/scraper.py
# Version: Gemini-2025-05-26 23:15 EDT

from bs4 import BeautifulSoup, Tag
from typing import Optional, List, Dict, Any, Set
from urllib.parse import urljoin, urlparse
import re

try:
    from .utils import logger, clean_text, extract_emails_from_text, normalize_email, make_absolute_url
    from .config import settings as global_app_settings
except ImportError:
    # Fallback for standalone execution or different environment
    from utils import logger, clean_text, extract_emails_from_text, normalize_email, make_absolute_url # type: ignore
    from config import settings as global_app_settings # type: ignore

# Regex to capture phone numbers, including common US/Canada formats and some international.
# Allows for letters in main parts for vanity numbers (e.g., 1-800-FLOWERS).
PHONE_REGEX_PATTERNS = [
    re.compile(r'''
        \b # Start at a word boundary
        (
            # Optional North American '1' or international prefix like +XX or 00XX
            (?:(?:(?:\+|00)\d{1,3}|1) [-\s.]*)?
            
            # Area Code part - optional, 3 alphanumeric chars, possibly in parentheses
            (?: \(? \s* ([A-Z0-9]{3}) \s* \)? [-\s.]*)?
            
            # Main number parts - typically XXX-XXXX or similar structure
            # Allows for alphanumeric characters (for vanity numbers)
            ([A-Z0-9]{3}) # Exchange part (3 alphanumeric)
            [-\s.]*
            ([A-Z0-9]{4}) # Subscriber part (4 alphanumeric)
            
            # Optional Extension
            (?: \s* (?:ext|x|ext\.?|extension) \s* (\d{1,5}) )?
        )
        \b # End at a word boundary
    ''', re.VERBOSE | re.IGNORECASE),
    re.compile(r''' # Simpler regex for blocks like +44 20 7946 0958 or just 7-11 digits/alphanum
        \b
        (
            (?:\+\d{1,3}[-\s.]?)? # Optional country code
            (?:[A-Z0-9][-\s.]*){6,14} # 6 to 14 alphanumeric chars with separators
            [A-Z0-9] 
        )
        (?!\d) # Not followed by a digit (to avoid grabbing parts of longer numbers)
    ''', re.VERBOSE | re.IGNORECASE)
]


# Dictionary for social media platform identification
SOCIAL_MEDIA_PLATFORMS = {
    "linkedin": "linkedin.com",
    "twitter": "twitter.com",
    "facebook": "facebook.com",
    "instagram": "instagram.com",
    "youtube": "youtube.com",
    "pinterest": "pinterest.com",
    "tiktok": "tiktok.com"
}
# More generic page titles that are unlikely to be company names
GENERIC_PAGE_TITLES = {
    "home", "contact", "contact us", "about", "about us", "services",
    "products", "login", "log in", "signin", "sign in", "search results",
    "not found", "error", "careers", "jobs", "blog", "news", "portfolio",
    "gallery", "faq", "support", "terms of service", "privacy policy",
    "sitemap", "request a quote", "get a demo", "solutions", "industries",
    "resources", "partners", "events", "press", "media", "investors",
    "shop", "store", "cart", "checkout", "my account", "dashboard",
    "portfolio", "projects", "team", "our team", "locations", "empty page"
}


class HTMLScraper:
    """
    Scrapes structured data from HTML content.
    """

    def __init__(self, html_content: str, source_url: str):
        if not html_content:
            logger.warning("HTMLScraper initialized with empty or None HTML content.")
            self.soup = BeautifulSoup("", "html.parser")
        else:
            self.soup = BeautifulSoup(html_content, "html.parser")
        self.source_url = source_url
        self.scraped_data: Dict[str, Any] = {}

    def _extract_text(self, element: Optional[Tag]) -> Optional[str]:
        if element:
            return clean_text(element.get_text(separator=' '))
        return None

    def _find_elements(self, selectors: List[str]) -> List[Tag]:
        found_elements: Set[Tag] = set()
        for selector in selectors:
            try:
                elements = self.soup.select(selector)
                for el in elements:
                    found_elements.add(el)
            except Exception as e:
                logger.warning(f"Error using selector '{selector}': {e}")
        return list(found_elements)

    def extract_company_name(self) -> Optional[str]:
        og_site_name_tag = self.soup.find("meta", property="og:site_name")
        if og_site_name_tag and og_site_name_tag.get("content"):
            name = clean_text(og_site_name_tag["content"])
            if name:
                logger.debug(f"Found company name via og:site_name: {name}")
                return name

        title_tag = self.soup.title
        if title_tag and title_tag.string:
            raw_title = clean_text(title_tag.string)
            if raw_title:
                if raw_title.lower() in GENERIC_PAGE_TITLES:
                    logger.debug(f"Title '{raw_title}' considered too generic for company name.")
                else:
                    common_separators = r"[\s]*[|\-–—:][\s]*"
                    parts = re.split(common_separators, raw_title)
                    potential_name = clean_text(parts[0])

                    if potential_name and len(potential_name) > 2 and potential_name.lower() not in GENERIC_PAGE_TITLES:
                        if not potential_name.isdigit() and len(potential_name.split()) <= 5:
                            logger.debug(f"Potential company name from title: {potential_name}")
                            return potential_name
                        else:
                            logger.debug(f"Title part '{potential_name}' deemed not suitable as company name (too long/generic after split, or numeric).")

        logger.info("Company name not definitively found.")
        return None

    def _normalize_phone_for_deduplication(self, phone_str: str) -> str:
        if not phone_str:
            return ""
        
        cleaned_phone = phone_str.strip().lower()
        has_plus = cleaned_phone.startswith('+')
        
        letter_map = {
            'a': '2', 'b': '2', 'c': '2', 'd': '3', 'e': '3', 'f': '3',
            'g': '4', 'h': '4', 'i': '4', 'j': '5', 'k': '5', 'l': '5',
            'm': '6', 'n': '6', 'o': '6', 'p': '7', 'q': '7', 'r': '7', 's': '7',
            't': '8', 'u': '8', 'v': '8', 'w': '9', 'x': '9', 'y': '9', 'z': '9'
        }
        
        normalized_output = []
        # Iterate over characters, skipping the initial '+' if present for letter mapping
        # but preserving its existence for the final output.
        temp_phone_for_mapping = cleaned_phone[1:] if has_plus else cleaned_phone
        
        for char_in_map_segment in temp_phone_for_mapping:
            if char_in_map_segment.isdigit():
                normalized_output.append(char_in_map_segment)
            elif char_in_map_segment in letter_map:
                normalized_output.append(letter_map[char_in_map_segment])
            # Non-digit, non-mappable letters, and other symbols are effectively stripped here for the key
        
        digits_part = "".join(normalized_output)
        
        # If the original had a plus, and the digits_part isn't empty (meaning it was a valid number)
        return f"+{digits_part}" if has_plus and digits_part else digits_part


    def _is_plausible_phone_number(self, normalized_phone: str) -> bool:
        if not normalized_phone:
            return False
        digit_count = 0
        for char in normalized_phone: # Count digits in the already normalized (letter-mapped) string
            if char.isdigit():
                digit_count +=1
        return 7 <= digit_count <= 15


    def extract_phone_numbers(self) -> List[str]:
        unique_phones_map: Dict[str, str] = {}

        # Strategy 1: Process `tel:` links
        tel_links = self.soup.select('a[href^="tel:"]')
        for link_tag in tel_links:
            href_attr = link_tag.get("href")
            if not href_attr:
                continue

            phone_from_href_raw = clean_text(href_attr.replace("tel:", ""))
            if not phone_from_href_raw:
                continue
            
            normalized_key_href = self._normalize_phone_for_deduplication(phone_from_href_raw)
            if not self._is_plausible_phone_number(normalized_key_href):
                logger.trace(f"Skipping implausible phone from href: '{phone_from_href_raw}' (normalized: '{normalized_key_href}')")
                continue

            preferred_display_phone = phone_from_href_raw 

            link_text_content = self._extract_text(link_tag)
            if link_text_content:
                cleaned_link_text = clean_text(link_text_content)
                if cleaned_link_text:
                    # Try to extract a phone number from the link text using regex
                    phone_part_from_text = ""
                    for pattern in PHONE_REGEX_PATTERNS:
                        match_in_link_text = pattern.search(cleaned_link_text)
                        if match_in_link_text:
                            extracted_part = clean_text(match_in_link_text.group(0).strip()) # Use group(0) for the whole match
                            # Check if this extracted part normalizes to the same as the href's number
                            if self._normalize_phone_for_deduplication(extracted_part) == normalized_key_href:
                                phone_part_from_text = extracted_part
                                break 
                    
                    if phone_part_from_text:
                        preferred_display_phone = phone_part_from_text
                        logger.debug(f"Preferred text version for tel link (extracted from text): '{preferred_display_phone}' (matched href normalized: '{normalized_key_href}')")
                    # If no specific part was extracted by regex from text,
                    # but the *entire* cleaned link text normalizes to the href's key,
                    # and the cleaned_link_text itself is a plausible phone number (e.g. "1-800-FLOWERS")
                    # then prefer the cleaned_link_text.
                    elif self._normalize_phone_for_deduplication(cleaned_link_text) == normalized_key_href:
                        is_link_text_plausible_phone = False
                        for pattern in PHONE_REGEX_PATTERNS:
                            if pattern.fullmatch(cleaned_link_text): # Check if full link text is a phone number
                                is_link_text_plausible_phone = True
                                break
                        if is_link_text_plausible_phone:
                            preferred_display_phone = cleaned_link_text
                            logger.debug(f"Preferred full link text for tel link: '{preferred_display_phone}' as it matches href normalized and is plausible phone format.")
                        # else, phone_from_href_raw remains preferred_display_phone

            # Add or update the phone number in the map
            if normalized_key_href not in unique_phones_map or \
               len(preferred_display_phone) > len(unique_phones_map[normalized_key_href]):
                if normalized_key_href in unique_phones_map:
                     logger.debug(f"Updating phone for key '{normalized_key_href}' from '{unique_phones_map[normalized_key_href]}' to more complete tel: link version '{preferred_display_phone}'")
                else:
                    logger.debug(f"Found phone via tel: link: '{preferred_display_phone}' (normalized key: '{normalized_key_href}')")
                unique_phones_map[normalized_key_href] = preferred_display_phone
            else:
                logger.trace(f"Duplicate phone (from tel: '{preferred_display_phone}', key: '{normalized_key_href}') already found as '{unique_phones_map[normalized_key_href]}', not updating.")


        # Strategy 2: Regex on text content of relevant elements
        text_search_elements = self.soup.select(
            'body p, body div, body span, body li, body td, body address, body footer, body header, body section, body article, body b, body strong, body font'
        )
        processed_elements_text = set()

        for element in text_search_elements:
            if element.name == 'a' and element.get('href', '').startswith('tel:'):
                continue # Already handled by tel: link strategy more specifically

            element_text = self._extract_text(element)
            if not element_text or len(element_text) < 7: # Basic filter
                continue
            
            # Avoid reprocessing identical text blocks that might come from overlapping selectors
            if element_text in processed_elements_text:
                continue
            processed_elements_text.add(element_text)

            for pattern in PHONE_REGEX_PATTERNS:
                matches = pattern.finditer(element_text)
                for match in matches:
                    phone_candidate_text = clean_text(match.group(0).strip()) # Use group(0) for the whole match
                    if phone_candidate_text:
                        normalized_key_text = self._normalize_phone_for_deduplication(phone_candidate_text)
                        if self._is_plausible_phone_number(normalized_key_text):
                            if normalized_key_text not in unique_phones_map or \
                               len(phone_candidate_text) > len(unique_phones_map[normalized_key_text]):
                                if normalized_key_text in unique_phones_map:
                                    logger.debug(f"Updating phone for key '{normalized_key_text}' from '{unique_phones_map[normalized_key_text]}' to more complete text regex version '{phone_candidate_text}'")
                                else:
                                    logger.debug(f"Found phone via text regex: '{phone_candidate_text}' (normalized key: '{normalized_key_text}')")
                                unique_phones_map[normalized_key_text] = phone_candidate_text
                            else:
                                logger.trace(f"Duplicate phone (from text regex: '{phone_candidate_text}', key: '{normalized_key_text}') already found as '{unique_phones_map[normalized_key_text]}', not updating.")
        
        found_phones_list = sorted(list(unique_phones_map.values()))
        logger.info(f"Found {len(found_phones_list)} unique phone number(s): {found_phones_list}")
        return found_phones_list

    def extract_emails(self) -> List[str]:
        all_emails: Set[str] = set()
        mailto_links = self.soup.select('a[href^="mailto:"]')
        for link in mailto_links:
            href = link.get("href")
            if href:
                email_candidate = clean_text(href.replace("mailto:", "").split('?')[0])
                normalized = normalize_email(email_candidate)
                if normalized:
                    logger.debug(f"Found email via mailto: link: {normalized}")
                    all_emails.add(normalized)

        body_tag = self.soup.body
        if body_tag:
            for text_node in body_tag.find_all(string=True, recursive=True):
                if text_node.parent.name in ['script', 'style']:
                    continue
                body_text_segment = clean_text(str(text_node))
                if body_text_segment:
                    emails_from_text = extract_emails_from_text(body_text_segment)
                    for email in emails_from_text:
                        normalized = normalize_email(email)
                        if normalized:
                            logger.debug(f"Found email via text regex: {normalized}")
                            all_emails.add(normalized)
        
        sorted_emails = sorted(list(all_emails))
        logger.info(f"Found {len(sorted_emails)} unique email address(es).")
        return sorted_emails

    def extract_addresses(self) -> List[str]:
        found_addresses: Set[str] = set()
        address_elements = self.soup.find_all(itemtype=lambda x: x and "PostalAddress" in x)
        for elem in address_elements:
            street_address = self._extract_text(elem.find(itemprop="streetAddress"))
            locality = self._extract_text(elem.find(itemprop="addressLocality"))
            region = self._extract_text(elem.find(itemprop="addressRegion"))
            postal_code = self._extract_text(elem.find(itemprop="postalCode"))
            country = self._extract_text(elem.find(itemprop="addressCountry"))

            parts = [p for p in [street_address, locality, region, postal_code, country] if p]
            if len(parts) >= 2:
                full_address = ", ".join(parts)
                logger.debug(f"Found address via schema.org: {full_address}")
                found_addresses.add(full_address)

        potential_address_containers = self.soup.select(
            'address, .address, .location, [class*="addr"], [id*="addr"], [class*="contact"] p, footer p, footer div'
        )
        processed_address_texts = set()

        for container in potential_address_containers:
            if container.get("itemtype") and "PostalAddress" in container.get("itemtype", ""):
                continue

            address_text = self._extract_text(container)
            if not address_text or len(address_text) < 10: 
                continue
            
            if address_text in processed_address_texts:
                continue
            processed_address_texts.add(address_text)

            if any(char.isdigit() for char in address_text) and \
               (any(kw in address_text.lower() for kw in ['street', 'road', 'ave', 'blvd', 'suite', 'floor', 'po box']) or \
                len(re.findall(r'\b\d{5}(?:-\d{4})?\b', address_text)) > 0 or \
                len(address_text.split(',')) >= 2):

                if len(address_text.split()) < 30: 
                    logger.debug(f"Potential address from class/tag search: {address_text}")
                    found_addresses.add(address_text)

        sorted_addresses = sorted(list(found_addresses))
        logger.info(f"Found {len(sorted_addresses)} potential address(es).")
        return sorted_addresses

    def extract_social_media_links(self) -> Dict[str, str]:
        social_links: Dict[str, str] = {}
        links = self.soup.find_all("a", href=True)

        for link_tag in links:
            href = link_tag.get("href")
            if not href:
                continue

            abs_href = make_absolute_url(self.source_url, href)
            if not abs_href:
                continue

            try:
                parsed_link = urlparse(abs_href)
                normalized_netloc = parsed_link.netloc.lower().replace("www.", "")
            except Exception:
                logger.warning(f"Could not parse URL for social media link: {abs_href}")
                continue

            for platform_key, platform_domain_pattern in SOCIAL_MEDIA_PLATFORMS.items():
                if platform_domain_pattern in normalized_netloc:
                    if platform_key == "linkedin" and not (parsed_link.path and parsed_link.path.strip('/') and ("company/" in parsed_link.path or "in/" in parsed_link.path or "school/" in parsed_link.path)):
                        continue 

                    if platform_key not in social_links:
                        logger.debug(f"Found social media link for {platform_key}: {abs_href}")
                        social_links[platform_key] = abs_href
                        break 
        
        logger.info(f"Found {len(social_links)} social media link(s).")
        return social_links

    def extract_description(self) -> Optional[str]:
        meta_desc = self.soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            description = clean_text(meta_desc["content"])
            if description:
                logger.debug(f"Found description via meta tag: {description[:100]}...")
                return description

        og_desc = self.soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            description = clean_text(og_desc["content"])
            if description:
                logger.debug(f"Found description via og:description: {description[:100]}...")
                return description

        logger.info("Description not found via meta tags.")
        return None

    def extract_canonical_url(self) -> Optional[str]:
        canonical_link = self.soup.find("link", rel="canonical")
        if canonical_link and canonical_link.get("href"):
            url = make_absolute_url(self.source_url, canonical_link["href"])
            if url:
                logger.debug(f"Found canonical URL: {url}")
                return url
        logger.info("Canonical URL not found.")
        return None

    def scrape(self) -> Dict[str, Any]:
        logger.info(f"Starting scrape for URL: {self.source_url}")

        self.scraped_data["company_name"] = self.extract_company_name()
        self.scraped_data["phone_numbers"] = self.extract_phone_numbers()
        self.scraped_data["emails"] = self.extract_emails()
        self.scraped_data["addresses"] = self.extract_addresses()
        self.scraped_data["social_media_links"] = self.extract_social_media_links()
        self.scraped_data["description"] = self.extract_description()
        self.scraped_data["canonical_url"] = self.extract_canonical_url()
        self.scraped_data["scraped_from_url"] = self.source_url

        parsed_source = urlparse(self.source_url)
        main_website = f"{parsed_source.scheme}://{parsed_source.netloc}"
        if self.scraped_data["canonical_url"]:
            parsed_canonical = urlparse(self.scraped_data["canonical_url"])
            if parsed_canonical.netloc:
                 main_website = f"{parsed_canonical.scheme}://{parsed_canonical.netloc}"
        self.scraped_data["website"] = main_website

        extracted_summary = {
            k: v for k, v in self.scraped_data.items()
            if not (v is None or (isinstance(v, (list, dict)) and not v))
        }
        logger.success(f"Scraping complete for {self.source_url}. Extracted: {extracted_summary}")

        return self.scraped_data

if __name__ == '__main__':
    sample_html = """
    <html>
        <head>
            <title>Test Company Inc. | Innovators</title>
            <meta name="description" content="We make amazing widgets for a better tomorrow.">
            <meta property="og:site_name" content="TestCo Widgets">
            <link rel="canonical" href="https://www.realtestco.com/home">
        </head>
        <body>
            <h1>Welcome to Test Company Inc.</h1>
            <p>Contact us at <a href="mailto:info@testco.com?subject=Inquiry">info@testco.com</a> or call us at <a href="tel:+1-800-555-1212">+1 (800) 555-1212</a>.</p>
            <p>Our support email is support@testco.com.</p>
            <p>Phone: (555) 123-4567 ext. 89</p>
            <p>Another identical number: +1 (800) 555-1212</p>
            <p>Support Line: 555-0123-7654</p>
            <p>Call 1-800-FLOWERS</p>
            <div class="address" itemprop itemtype="http://schema.org/PostalAddress">
                <span itemprop="streetAddress">123 Main St</span>,
                <span itemprop="addressLocality">Anytown</span>,
                <span itemprop="addressRegion">CA</span>
                <span itemprop="postalCode">90210</span>
            </div>
            <div class="social">
                <a href="https://www.linkedin.com/company/testco">LinkedIn</a>
                <a href="http://twitter.com/testco_widgets">Twitter</a>
                <a href="https://www.facebook.com/TestCoWidgetsPage/">Our Facebook Page</a>
            </div>
            <footer>
                Another contact: (555) 987-6543. General inquiries: general@testco.com. Phone: 1-888-555-DATA.
            </footer>
        </body>
    </html>
    """
    test_url = "https://www.originaltestco.com/somepage"
    scraper = HTMLScraper(html_content=sample_html, source_url=test_url)
    data = scraper.scrape()

    import json
    print(json.dumps(data, indent=4))
