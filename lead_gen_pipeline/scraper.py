# lead_gen_pipeline/scraper.py
# HTML scraping and business data extraction

from bs4 import BeautifulSoup, Tag, NavigableString
from typing import Optional, List, Dict, Any, Set, Tuple
from urllib.parse import urljoin, urlparse
import re
import unicodedata

try:
    from .utils import logger, clean_text, extract_emails_from_text, normalize_email, make_absolute_url
    from .config import settings as global_app_settings
    from .placeholder_data import (
        GENERIC_PHONE_PATTERNS, GENERIC_EMAIL_PATTERNS, GENERIC_EMAIL_DOMAINS,
        GENERIC_COMPANY_TERMS, GENERIC_SOCIAL_MEDIA_PATHS,
        PLACEHOLDER_WEBSITE_DOMAINS, PLACEHOLDER_TLDS
    )
except ImportError:
    try:
        from lead_gen_pipeline.utils import logger, clean_text, extract_emails_from_text, normalize_email, make_absolute_url
        from lead_gen_pipeline.config import settings as global_app_settings
        from lead_gen_pipeline.placeholder_data import (
            GENERIC_PHONE_PATTERNS, GENERIC_EMAIL_PATTERNS, GENERIC_EMAIL_DOMAINS,
            GENERIC_COMPANY_TERMS, GENERIC_SOCIAL_MEDIA_PATHS,
            PLACEHOLDER_WEBSITE_DOMAINS, PLACEHOLDER_TLDS
        )
    except ImportError:
        # Fallback imports
        class DummyLogger:
            def info(self, msg): print(f"INFO: {msg}")
            def warning(self, msg): print(f"WARNING: {msg}")
            def error(self, msg): print(f"ERROR: {msg}")
            def debug(self, msg): print(f"DEBUG: {msg}")
            def success(self, msg): print(f"SUCCESS: {msg}")
        logger = DummyLogger()
        def clean_text(text): return text.strip() if text else None
        def extract_emails_from_text(text): return re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text or "")
        def normalize_email(email): return email.lower() if email else None
        def make_absolute_url(base, rel): return urljoin(base, rel) if rel else None
        
        GENERIC_PHONE_PATTERNS = {"555-0100", "123-456-7890", "555-555-5555", "000-000-0000"}
        GENERIC_EMAIL_PATTERNS = {"email@example.com", "test@example.com", "info@example.com"}
        GENERIC_EMAIL_DOMAINS = {"example.com", "domain.com", "test.com"}
        GENERIC_COMPANY_TERMS = {"home", "about", "contact", "welcome to", "basic contact", "no info", "login"}
        GENERIC_SOCIAL_MEDIA_PATHS = {"login", "share", "search", "help"}
        PLACEHOLDER_WEBSITE_DOMAINS = {"example.com", "test.com"}
        PLACEHOLDER_TLDS = {".test", ".example"}

# Optional dependencies
try:
    import phonenumbers
    from phonenumbers import PhoneNumberFormat, NumberParseException
    PHONENUMBERS_AVAILABLE = True
except ImportError:
    phonenumbers = None
    PhoneNumberFormat = None
    NumberParseException = None
    PHONENUMBERS_AVAILABLE = False
    logger.warning("phonenumbers library not available")

try:
    import spacy
    try:
        NLP_SPACY = spacy.load("en_core_web_sm")
    except OSError:
        NLP_SPACY = None
except ImportError:
    spacy = None
    NLP_SPACY = None

try:
    from email_validator import validate_email, EmailNotValidError
    EMAIL_VALIDATOR_AVAILABLE = True
except ImportError:
    validate_email = None
    EmailNotValidError = None
    EMAIL_VALIDATOR_AVAILABLE = False

SOCIAL_MEDIA_PLATFORMS = {
    "linkedin": {
        "domains": ["linkedin.com", "www.linkedin.com"],
        "valid_paths": ["/company/", "/in/", "/school/", "/pub/"],
        "exclude_paths": ["login", "signup", "help", "legal", "feed", "shareArticle"]
    },
    "twitter": {
        "domains": ["twitter.com", "www.twitter.com", "x.com", "www.x.com"],
        "username_pattern": r"^[A-Za-z0-9_]{1,15}$",
        "exclude_paths": ["search", "intent", "login", "home", "explore", "settings", "i/"]
    },
    "facebook": {
        "domains": ["facebook.com", "www.facebook.com", "fb.com"],
        "valid_paths": ["/pages/", "/pg/"],
        "username_pattern": r"^[a-zA-Z0-9._-]+/?$",
        "exclude_paths": ["login", "sharer", "dialog", "help", "terms", "ads"]
    },
    "instagram": {
        "domains": ["instagram.com", "www.instagram.com"],
        "username_pattern": r"^[A-Za-z0-9_.\-]+/?$",
        "exclude_paths": ["/p/", "/reels/", "/explore/", "/accounts/", "login"]
    },
    "youtube": {
        "domains": ["youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"],
        "valid_paths": ["/channel/", "/c/", "/user/", "/@"],
        "username_pattern": r"^[A-Za-z0-9_.-]+$",
        "exclude_paths": ["/watch", "/embed", "/results", "/shorts", "login", "account"]
    },
    "pinterest": {
        "domains": ["pinterest.com", "www.pinterest.com", "pinterest.co.uk"],
        "username_pattern": r"^[A-Za-z0-9_]+/?$",
        "exclude_paths": ["/pin/", "/search/", "login", "/settings/"]
    },
    "tiktok": {
        "domains": ["tiktok.com", "www.tiktok.com"],
        "username_pattern": r"^@[A-Za-z0-9_.]+$",
        "exclude_paths": ["/tag/", "/search", "login", "/upload"]
    }
}

class HTMLScraper:
    def __init__(self, html_content: str, source_url: str):
        if not html_content:
            logger.warning(f"Empty HTML content for URL: {source_url}")
            self.soup = BeautifulSoup("", "html.parser")
        else:
            self.soup = BeautifulSoup(html_content, "html.parser")
        self.source_url = source_url
        self.default_region = "US"

    def _is_generic_phone(self, phone_text: str) -> bool:
        """Check if phone number is placeholder/generic."""
        if not phone_text:
            return False
        
        normalized = re.sub(r'[^\da-zA-Z]', '', phone_text).lower()
        
        for pattern in GENERIC_PHONE_PATTERNS:
            pattern_normalized = re.sub(r'[^\da-zA-Z]', '', pattern).lower()
            if pattern_normalized == normalized:
                return True
        
        # Check for repeated digits
        digits_only = re.sub(r'\D', '', phone_text)
        if len(digits_only) >= 7 and len(set(digits_only)) == 1:
            return True
            
        return False

    def _is_generic_email(self, email_text: str) -> bool:
        """Check if email is placeholder/generic."""
        if not email_text:
            return False
            
        email_lower = email_text.lower()
        
        if email_lower in GENERIC_EMAIL_PATTERNS:
            return True
            
        try:
            domain = email_lower.split('@')[1]
            if domain in GENERIC_EMAIL_DOMAINS:
                return True
            if any(domain.endswith(tld) for tld in PLACEHOLDER_TLDS):
                return True
        except (IndexError, AttributeError):
            pass
            
        return False

    def _extract_text_content(self, element: Optional[Tag]) -> Optional[str]:
        """Extract and clean text from element."""
        if not element:
            return None
            
        try:
            text = element.get_text(separator=' ', strip=True)
        except Exception:
            texts = []
            for item in element.descendants:
                if isinstance(item, NavigableString):
                    parent_name = getattr(item.parent, 'name', '')
                    if parent_name not in ['script', 'style', 'noscript']:
                        texts.append(str(item))
            text = ' '.join(texts)
        
        if not text:
            return None
            
        # Unicode normalization
        text = unicodedata.normalize('NFKC', text)
        text = text.replace('\xa0', ' ')
        
        # Normalize hyphens
        for char in "‑–—−‒―‐":
            text = text.replace(char, '-')
            
        text = clean_text(text)
        return text if text else None

    def extract_company_name(self) -> Optional[str]:
        """Extract company name from various page elements."""
        candidates = []

        # og:site_name meta tag
        og_site_name = self.soup.find("meta", property="og:site_name")
        if og_site_name and og_site_name.get("content"):
            name = clean_text(og_site_name["content"])
            if name and name.lower() not in GENERIC_COMPANY_TERMS:
                candidates.append((name, 10))

        # Schema.org Organization
        org_schema = self.soup.find(itemtype=lambda x: x and "Organization" in x)
        if org_schema:
            name_elem = org_schema.find(itemprop="name")
            if name_elem:
                name = self._extract_text_content(name_elem)
                if name and name.lower() not in GENERIC_COMPANY_TERMS:
                    candidates.append((name, 9))

        # og:title with parsing
        og_title = self.soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title_content = clean_text(og_title["content"])
            if title_content and title_content.lower() not in GENERIC_COMPANY_TERMS:
                parts = re.split(r'\s*[\|\-–—]\s*', title_content)
                if len(parts) > 1:
                    company_part = clean_text(parts[-1])
                    if company_part and company_part.lower() not in GENERIC_COMPANY_TERMS:
                        candidates.append((company_part, 8))
                else:
                    candidates.append((title_content, 6))

        # Page title
        title_tag = self.soup.title
        if title_tag:
            title_text = self._extract_text_content(title_tag)
            if title_text and title_text.lower() not in GENERIC_COMPANY_TERMS:
                parts = re.split(r'\s*[\|\-–—]\s*', title_text)
                if len(parts) > 1:
                    company_part = clean_text(parts[-1])
                    if company_part and company_part.lower() not in GENERIC_COMPANY_TERMS:
                        candidates.append((company_part, 7))

        # Copyright footer
        footer = self.soup.find("footer")
        if footer:
            footer_text = self._extract_text_content(footer)
            if footer_text:
                copyright_match = re.search(
                    r'©\s*(?:\d{4}[-\s]?\d{4}|\d{4})?\s*([^.,\n]+?)(?:\s*(?:All Rights Reserved|Inc\.?|LLC|Ltd\.?|Corp\.?))?(?:\.|$)',
                    footer_text, re.IGNORECASE
                )
                if copyright_match:
                    company_name = clean_text(copyright_match.group(1))
                    if company_name and company_name.lower() not in GENERIC_COMPANY_TERMS:
                        candidates.append((company_name, 6))

        # NLP extraction fallback
        if NLP_SPACY and not candidates:
            h1 = self.soup.find('h1')
            if h1:
                h1_text = self._extract_text_content(h1)
                if h1_text and len(h1_text) < 100:
                    try:
                        doc = NLP_SPACY(h1_text)
                        for ent in doc.ents:
                            if ent.label_ == "ORG":
                                org_name = clean_text(ent.text)
                                if org_name and org_name.lower() not in GENERIC_COMPANY_TERMS:
                                    candidates.append((org_name, 4))
                    except Exception:
                        pass

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _decode_cloudflare_email(self, encoded_string: str) -> Optional[str]:
        """Decode Cloudflare email protection."""
        try:
            if encoded_string.startswith("/cdn-cgi/l/email-protection#"):
                encoded_string = encoded_string.split("#")[-1]
            
            if len(encoded_string) < 2:
                return None
                
            r = int(encoded_string[:2], 16)
            email = ''.join([
                chr(int(encoded_string[i:i+2], 16) ^ r) 
                for i in range(2, len(encoded_string), 2)
            ])
            return email
        except (ValueError, IndexError):
            return None

    def _clean_phone_text(self, text: str) -> str:
        """Clean phone number text."""
        if not text:
            return ""
        
        text = re.sub(r'^(?:phone|tel|call|fax):?\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*(?:ext|x|extension)\.?\s*\d+\s*$', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Handle vanity numbers
        parts = text.split()
        cleaned_parts = []
        current_vanity = []
        
        for part in parts:
            if re.match(r'^[A-Z]+$', part) and len(part) > 1:
                current_vanity.append(part)
            else:
                if current_vanity:
                    cleaned_parts.append(''.join(current_vanity))
                    current_vanity = []
                cleaned_parts.append(part)
        
        if current_vanity:
            cleaned_parts.append(''.join(current_vanity))
            
        return ' '.join(cleaned_parts)

    def _parse_phone_number(self, phone_text: str) -> Optional[str]:
        """Parse phone number to E164 format."""
        if not PHONENUMBERS_AVAILABLE or not phone_text:
            return None
            
        phone_text = self._clean_phone_text(phone_text)
        
        if self._is_generic_phone(phone_text):
            return None
            
        try:
            number = phonenumbers.parse(phone_text, self.default_region)
            if phonenumbers.is_valid_number(number):
                return phonenumbers.format_number(number, PhoneNumberFormat.E164)
                
            if not phone_text.startswith('+'):
                number = phonenumbers.parse(phone_text, None)
                if phonenumbers.is_valid_number(number):
                    return phonenumbers.format_number(number, PhoneNumberFormat.E164)
                    
        except NumberParseException:
            pass
            
        return None

    def extract_phone_numbers(self) -> List[str]:
        """Extract phone numbers from HTML."""
        if not PHONENUMBERS_AVAILABLE:
            return []
            
        phones = set()

        # Extract from tel: links
        for link in self.soup.find_all("a", href=True):
            href = link.get("href", "")
            if href.startswith("tel:"):
                phone_text = href.replace("tel:", "")
                parsed = self._parse_phone_number(phone_text)
                if parsed:
                    phones.add(parsed)
                    
            # Check link text
            link_text = self._extract_text_content(link)
            if link_text and any(char.isdigit() for char in link_text):
                parsed = self._parse_phone_number(link_text)
                if parsed:
                    phones.add(parsed)

        # Extract from text content
        selectors = [
            'p', 'div', 'span', 'address', 'footer', 
            '[class*="contact"]', '[class*="phone"]', '[class*="tel"]'
        ]
        
        for selector in selectors:
            try:
                for element in self.soup.select(selector):
                    text = self._extract_text_content(element)
                    if not text:
                        continue
                        
                    phone_patterns = [
                        r'\+?1?[-.\s]?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})',
                        r'\+?(\d{1,3})[-.\s]?(\d{3,4})[-.\s]?(\d{3,4})[-.\s]?(\d{3,4})',
                        r'\b1[-.\s]?800[-.\s]?[A-Z]{3}[-.\s]?[A-Z]{4}\b',
                    ]
                    
                    for pattern in phone_patterns:
                        matches = re.finditer(pattern, text, re.IGNORECASE)
                        for match in matches:
                            parsed = self._parse_phone_number(match.group(0))
                            if parsed:
                                phones.add(parsed)
            except Exception:
                continue

        return sorted(list(phones))

    def extract_emails(self) -> List[str]:
        """Extract email addresses from HTML."""
        emails = set()

        # Cloudflare protection
        for link in self.soup.find_all("a", href=True):
            href = link.get("href", "")
            if "email-protection" in href:
                decoded = self._decode_cloudflare_email(href)
                if decoded and not self._is_generic_email(decoded):
                    emails.add(normalize_email(decoded))

        # mailto links
        for link in self.soup.find_all("a", href=True):
            href = link.get("href", "")
            if href.startswith("mailto:"):
                email = href.replace("mailto:", "").split('?')[0]
                email = clean_text(email)
                if email and not self._is_generic_email(email):
                    normalized = normalize_email(email)
                    if normalized:
                        emails.add(normalized)

        # Text content with deobfuscation
        text_elements = self.soup.find_all(['p', 'div', 'span', 'address', 'footer'])
        for element in text_elements:
            text = self._extract_text_content(element)
            if not text:
                continue
                
            # Deobfuscate patterns
            text = re.sub(r'\s*\[at\]\s*', '@', text, flags=re.IGNORECASE)
            text = re.sub(r'\s*\(at\)\s*', '@', text, flags=re.IGNORECASE)
            text = re.sub(r'\s+at\s+', '@', text, flags=re.IGNORECASE)
            text = re.sub(r'\s*\[dot\]\s*', '.', text, flags=re.IGNORECASE)
            text = re.sub(r'\s*\(dot\)\s*', '.', text, flags=re.IGNORECASE)
            text = re.sub(r'\s+dot\s+', '.', text, flags=re.IGNORECASE)
            
            found_emails = extract_emails_from_text(text)
            for email in found_emails:
                if not self._is_generic_email(email):
                    emails.add(email)

        # Validate if library available
        if EMAIL_VALIDATOR_AVAILABLE:
            validated_emails = []
            for email in emails:
                try:
                    valid_email = validate_email(email, check_deliverability=False)
                    validated_emails.append(valid_email.normalized)
                except EmailNotValidError:
                    continue
            return sorted(validated_emails)
        
        return sorted(list(emails))

    def extract_addresses(self) -> List[str]:
        """Extract addresses from HTML."""
        addresses = set()

        # Schema.org markup
        for address_elem in self.soup.find_all(itemtype=lambda x: x and "PostalAddress" in x):
            parts = []
            
            street = address_elem.find(itemprop="streetAddress")
            if street:
                parts.append(self._extract_text_content(street))
                
            city = address_elem.find(itemprop="addressLocality")
            if city:
                parts.append(self._extract_text_content(city))
                
            region = address_elem.find(itemprop="addressRegion")
            postcode = address_elem.find(itemprop="postalCode")
            
            if region and postcode:
                parts.append(f"{self._extract_text_content(region)} {self._extract_text_content(postcode)}")
            elif region:
                parts.append(self._extract_text_content(region))
            elif postcode:
                parts.append(self._extract_text_content(postcode))
                
            if len(parts) >= 2:
                address = ", ".join(filter(None, parts))
                if address:
                    addresses.add(address)

        # Common containers
        selectors = ['address', '.address', '.location', '[class*="addr"]', 'footer']
        
        for selector in selectors:
            try:
                for element in self.soup.select(selector):
                    text = self._extract_text_content(element)
                    if not text or len(text) < 10:
                        continue
                        
                    # Basic address pattern matching
                    if re.search(r'\d+\s+\w+.*\b[A-Z]{2}\b\s+\d{5}', text):
                        addresses.add(text)
                    elif re.search(r'\d+.*\w+.*\d{5}', text):
                        addresses.add(text)
            except Exception:
                continue

        return sorted(list(addresses))

    def _is_valid_social_url(self, url: str, platform: str) -> bool:
        """Validate social media URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace("www.", "")
            path = parsed.path.strip('/')
            
            platform_config = SOCIAL_MEDIA_PLATFORMS.get(platform, {})
            
            if domain not in platform_config.get("domains", []):
                return False
                
            exclude_paths = platform_config.get("exclude_paths", [])
            for exclude in exclude_paths:
                if exclude in path.lower():
                    return False
                    
            valid_paths = platform_config.get("valid_paths", [])
            if valid_paths:
                if not any(path.startswith(vp.strip('/')) for vp in valid_paths):
                    return False
            else:
                username_pattern = platform_config.get("username_pattern")
                if username_pattern:
                    username = path.split('/')[0] if path else ""
                    if platform == "tiktok" and not username.startswith('@'):
                        username = f"@{username}"
                    if not re.match(username_pattern, username):
                        return False
                        
            return True
            
        except Exception:
            return False

    def extract_social_media_links(self) -> Dict[str, str]:
        """Extract social media profile links."""
        social_links = {}
        
        for link in self.soup.find_all("a", href=True):
            href = link.get("href", "")
            if not href:
                continue
                
            abs_url = make_absolute_url(self.source_url, href)
            if not abs_url:
                continue
                
            for platform, config in SOCIAL_MEDIA_PLATFORMS.items():
                if platform in social_links:
                    continue
                    
                if self._is_valid_social_url(abs_url, platform):
                    social_links[platform] = abs_url
                    break
                    
        return social_links

    def extract_description(self) -> Optional[str]:
        """Extract page description."""
        meta_tags = [
            {"property": "og:description"},
            {"name": "description"},
            {"name": "twitter:description"}
        ]
        
        for attrs in meta_tags:
            meta = self.soup.find("meta", attrs=attrs)
            if meta and meta.get("content"):
                desc = clean_text(meta["content"])
                if desc and len(desc) > 10 and desc.lower() not in GENERIC_COMPANY_TERMS:
                    return desc
                    
        return None

    def extract_canonical_url(self) -> Optional[str]:
        """Extract canonical URL."""
        canonical = self.soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            return make_absolute_url(self.source_url, canonical["href"])
        return None

    def scrape(self) -> Dict[str, Any]:
        """Main scraping method."""
        logger.info(f"Scraping URL: {self.source_url}")
        
        data = {
            "company_name": self.extract_company_name(),
            "phone_numbers": self.extract_phone_numbers(),
            "emails": self.extract_emails(),
            "addresses": self.extract_addresses(),
            "social_media_links": self.extract_social_media_links(),
            "description": self.extract_description(),
            "canonical_url": self.extract_canonical_url(),
            "scraped_from_url": self.source_url
        }
        
        # Extract website from source URL
        try:
            parsed = urlparse(self.source_url)
            if parsed.scheme and parsed.netloc:
                website = f"{parsed.scheme}://{parsed.netloc}"
                if parsed.netloc.lower() not in PLACEHOLDER_WEBSITE_DOMAINS:
                    data["website"] = website
                else:
                    data["website"] = None
            else:
                data["website"] = None
        except Exception:
            data["website"] = None
            
        logger.success(f"Scraping complete: {self.source_url}")
        return data
