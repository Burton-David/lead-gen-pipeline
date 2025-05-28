# lead_gen_pipeline/scraper.py
# Version: v6 (incorporating discussed improvements)

from bs4 import BeautifulSoup, Tag, NavigableString
from typing import Optional, List, Dict, Any, Set, Tuple
from urllib.parse import urljoin, urlparse
import re
import unicodedata

try:
    from .utils import logger, clean_text, extract_emails_from_text, normalize_email, make_absolute_url
    from .config import settings as global_app_settings
except ImportError:
    # Fallback for direct execution or different environment
    from utils import logger, clean_text, extract_emails_from_text, normalize_email, make_absolute_url # type: ignore
    from config import settings as global_app_settings # type: ignore

# --- Library Imports with Fallbacks ---
try:
    import phonenumbers
    from phonenumbers import PhoneNumberFormat, NumberParseException, PhoneNumberMatcher, Leniency
except ImportError:
    phonenumbers = None # type: ignore
    PhoneNumberFormat = None # type: ignore
    NumberParseException = None # type: ignore
    PhoneNumberMatcher = None # type: ignore
    Leniency = None # type: ignore
    logger.error("CRITICAL: 'phonenumbers' library not found. Phone number extraction will be severely limited.")

try:
    import spacy
    try:
        NLP_SPACY = spacy.load("en_core_web_sm")
    except OSError:
        NLP_SPACY = None
        logger.warning("spaCy model 'en_core_web_sm' not found. NER for company name disabled.")
except ImportError:
    spacy = None
    NLP_SPACY = None
    logger.warning("spaCy library not found. NER for company name disabled.")

try:
    from email_validator import validate_email, EmailNotValidError
except ImportError:
    validate_email = None
    EmailNotValidError = None # type: ignore
    logger.warning("email-validator library not found. Advanced email validation disabled.")

try:
    from usaddress import tag as usaddress_tag_func, RepeatedLabelError as USAddressRepeatedLabelError
except ImportError:
    usaddress_tag_func = None
    USAddressRepeatedLabelError = None # type: ignore
    logger.warning("usaddress library not found. US address parsing limited.")

try:
    from postal.parser import parse_address as libpostal_parse_address_func
    from postal.expand import expand_address as libpostal_expand_address_func
except ImportError:
    libpostal_parse_address_func = None
    libpostal_expand_address_func = None # type: ignore
    logger.warning("pypostal (libpostal) library not found. International address parsing disabled.")

# --- Constants ---
SOCIAL_MEDIA_PLATFORMS = {
    "linkedin": {
        "domain": "linkedin.com",
        "path_prefixes": ["/company/", "/in/", "/school/", "/pub/", "/showcase/"],
        "path_exclusions": ["/feed/", "/shareArticle", "/posts/", "/login", "/signup", "/help/", "/legal/"]
    },
    "twitter": {
        "domain": "x.com",
        "alt_domains": ["twitter.com"],
        "path_regex": r"^[A-Za-z0-9_]{1,15}$",
        "path_exclusions": ["search", "hashtag", "intent", "home", "share", "widgets", "status/", "i/web", "login", "explore", "notifications", "messages", "compose", "settings", "following", "followers", "lists", "communities", "premium_subscribe"]
    },
    "facebook": {
        "domain": "facebook.com",
        "path_prefixes": ["/pages/", "/pg/"],
        "path_regex": r"^[a-zA-Z0-9._-]+/?$",
        "profile_php": "profile.php",
        "path_exclusions": ["sharer", "dialog/", "plugins", "video.php", "photo.php", "story.php", "watch", "events", "login.php", "marketplace", "gaming", "developer", "notes/", "media/set/", "groups/", "ads/"]
    },
    "instagram": {
        "domain": "instagram.com",
        "path_regex": r"^[A-Za-z0-9_.\-]+/?$",
        "path_exclusions": ["/p/", "/reels/", "/stories/", "/explore/", "/accounts/", "/direct/"]
    },
    "youtube": {
        "domain": "youtube.com",
        "alt_domains": [
            "m.youtube.com", "m.youtube.com",
            "music.youtube.com", "music.youtube.com",
            "youtube.com", "m.youtube.com",
            "youtu.be", "m.youtube.com"
        ],
        "path_prefixes": ["/channel/", "/c/", "/user/", "/@"],
        "path_regex": r"^[A-Za-z0-9_.-]+$",
        "path_exclusions": [
            "/watch", "/embed", "/feed", "/playlist", "/results", "/redirect",
            "/shorts", "/live", "/community", "/store", "/music", "/premium",
            "/account", "/feed/subscriptions", "/feed/history", "results?search_query=",
            "/t/", "/s/", "/clip/"
        ]
    },
    "pinterest": {
        "domain": "pinterest.com",
        "path_regex": r"^[A-Za-z0-9_]+/?$",
        "path_exclusions": ["/pin/", "/ideas/", "/search/", "/settings/", "/login/"]
    },
    "tiktok": {
        "domain": "tiktok.com",
        "path_regex": r"^@[A-Za-z0-9_.]+$",
        "path_exclusions": ["/tag/", "/music/", "/trending", "/foryou", "/search", "/upload", "/messages", "/live", "/explore", "/following", "/friends"]
    }
}

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
    def __init__(self, html_content: str, source_url: str):
        if not html_content:
            logger.warning(f"HTMLScraper initialized with empty or None HTML content for URL: {source_url}")
            self.soup = BeautifulSoup("", "html.parser")
        else:
            self.soup = BeautifulSoup(html_content, "html.parser")
        self.source_url = source_url
        self.default_region = "US" # Can be overridden
        self.scraped_data: Dict[str, Any] = {}



    def _extract_text_content(self, element: Optional[Tag]) -> Optional[str]:
        if not element:
            return None

        try:
            # Use BeautifulSoup's built-in method for robust text extraction
            full_text = element.get_text(separator=' ', strip=True)
        except Exception as e:
            logger.debug(f"element.get_text() failed: {e}. Falling back to manual iteration for _extract_text_content.")
            # Fallback to manual iteration if .get_text() fails (should be rare)
            texts = []
            for descendant in element.descendants:
                if isinstance(descendant, NavigableString):
                    if descendant.parent.name in ['script', 'style', 'noscript', 'meta', 'link', 'head', 'button', 'option', 'select', 'textarea', 'input', 'title']:
                        continue
                    stripped_text = str(descendant).strip() # Strip individual parts
                    if stripped_text:
                        texts.append(stripped_text)
                elif isinstance(descendant, Tag):
                    if descendant.name == 'br': # Treat <br> as a space
                        if texts and not texts[-1].isspace(): # Add space if last part wasn't already space-like
                            texts.append(' ')
            full_text = " ".join(texts) # Join with spaces, then clean_text will handle multiples and final strip

        if not full_text:
            return None # Return None if no text was extracted
            
        # Unicode Normalization (NFKC is good for compatibility and composing characters)
        normalized_text = unicodedata.normalize('NFKC', full_text)
        
        # Hyphen Replacement (ensure this is using the correct hyphen_like_chars string)
        hyphen_like_chars = "‑–—−‒―‐" # U+2011, U+2013, U+2014, U+2212 (true minus), U+2012, U+2015, U+2010
        for char in hyphen_like_chars:
            normalized_text = normalized_text.replace(char, '-')
        
        # NBSP to space
        normalized_text = normalized_text.replace('\xa0', ' ')
        
        # Use existing clean_text from utils.py which should handle collapsing multiple spaces and stripping.
        final_text = clean_text(normalized_text)

        if final_text:
            # Additional step: Remove spaces before common sentence-ending punctuation.
            # This targets cases like "word ." -> "word."
            final_text = re.sub(r'\s+([.,;:!?])', r'\1', final_text)
        
        return final_text if final_text else None
    def extract_company_name(self) -> Optional[str]:
        # Logic from v5, using new _extract_text_content where applicable
        candidates: List[Tuple[str, int]] = []

        og_site_name_tag = self.soup.find("meta", property="og:site_name")
        if og_site_name_tag and og_site_name_tag.get("content"):
            name = clean_text(og_site_name_tag["content"])
            if name and name.lower() not in GENERIC_PAGE_TITLES:
                candidates.append((name, 10))

        og_title_tag = self.soup.find("meta", property="og:title")
        if og_title_tag and og_title_tag.get("content"):
            name = clean_text(og_title_tag["content"])
            if name and name.lower() not in GENERIC_PAGE_TITLES:
                parts = re.split(r"[\s]*[|\-–—:][\s]*", name, 1)
                candidate_name = clean_text(parts[0])
                if candidate_name and len(candidate_name.split()) <= 5 and candidate_name.lower() not in GENERIC_PAGE_TITLES:
                    candidates.append((candidate_name, 8))

        title_tag = self.soup.title
        if title_tag and title_tag.string: # title.string is already NavigableString
            raw_title = clean_text(str(title_tag.string))
            if raw_title and raw_title.lower() not in GENERIC_PAGE_TITLES:
                common_separators = r"[\s]*[|\-–—:][\s]*"
                title_parts = re.split(common_separators, raw_title)
                for part_text in title_parts:
                    cleaned_part = clean_text(part_text)
                    if (cleaned_part and cleaned_part.lower() not in GENERIC_PAGE_TITLES and
                        len(cleaned_part) > 1 and not cleaned_part.isdigit() and
                        len(cleaned_part.split()) <= 5):
                        candidates.append((cleaned_part, 7))
                        break

        org_schema = self.soup.find(itemtype=lambda x: x and "Organization" in x)
        if org_schema:
            name_tag = org_schema.find(itemprop="name")
            if name_tag:
                name = self._extract_text_content(name_tag) # Use refined extraction
                if name and name.lower() not in GENERIC_PAGE_TITLES:
                    candidates.append((name, 9))

        if NLP_SPACY:
            text_sources = []
            h1 = self.soup.find('h1')
            if h1: text_sources.append(self._extract_text_content(h1))
            
            for selector in ['.site-title', '.logo-text', '[class*="brand"]', '[id*="brand"]', '.navbar-brand']:
                elem = self.soup.select_one(selector)
                if elem: text_sources.append(self._extract_text_content(elem))
            
            footer = self.soup.find("footer")
            if footer:
                footer_text = self._extract_text_content(footer)
                if footer_text:
                    copy_match = re.search(r"(?:©|copyright)\s*(?:\d{4}\s*)?([^.,;:\n<]+)", footer_text, re.IGNORECASE)
                    if copy_match and copy_match.group(1):
                        company_from_copyright = clean_text(copy_match.group(1).replace("All Rights Reserved", "").strip())
                        if (company_from_copyright and len(company_from_copyright.split()) <= 5 and
                            company_from_copyright.lower() not in GENERIC_PAGE_TITLES):
                            candidates.append((company_from_copyright, 6))

            for text_content in filter(None, text_sources):
                if text_content and len(text_content) > 500: text_content = text_content[:500] # Limit NER input length
                if text_content:
                    try:
                        doc = NLP_SPACY(text_content)
                        for ent in doc.ents:
                            if ent.label_ == "ORG":
                                org_name = clean_text(ent.text)
                                if (org_name and len(org_name.split()) <= 5 and len(org_name) > 2 and
                                    org_name.lower() not in GENERIC_PAGE_TITLES):
                                    candidates.append((org_name, 5))
                    except Exception as e:
                        logger.debug(f"spaCy processing error for company name: {e}")
        
        if not candidates:
            logger.info(f"Company name not found for {self.source_url}")
            return None

        unique_names = {}
        for name, score in candidates:
            name_lower = name.lower()
            if (name_lower not in unique_names or
                score > unique_names[name_lower][1] or
                (score == unique_names[name_lower][1] and len(name) > len(unique_names[name_lower][0]))):
                unique_names[name_lower] = (name, score)
        
        if not unique_names: return None
        sorted_candidates = sorted(list(unique_names.values()), key=lambda x: (x[1], len(x[0])), reverse=True)
        final_name = sorted_candidates[0][0]
        logger.debug(f"Selected company name: '{final_name}' for {self.source_url}")
        return final_name

    def _decode_cloudflare_email(self, encoded_string: str) -> Optional[str]:
        try:
            if encoded_string.startswith("/cdn-cgi/l/email-protection#"):
                encoded_string = encoded_string.split("#")[-1]
            if len(encoded_string) < 2: return None
            r = int(encoded_string[:2], 16)
            email = ''.join([chr(int(encoded_string[i:i+2], 16) ^ r) for i in range(2, len(encoded_string), 2)])
            return email
        except Exception: return None

# In class HTMLScraper:
# In class HTMLScraper:
# In class HTMLScraper
    def _parse_phone_string_direct(self, phone_string: Optional[str], region: Optional[str] = None) -> Optional[str]:
        if not phonenumbers or not phone_string:
            # print(f"DEBUG: _parse_phone_string_direct: Early exit - phonenumbers: {bool(phonenumbers)}, phone_string: '{phone_string}'")
            return None
        
        phone_string_to_parse = phone_string.strip()
        if not phone_string_to_parse:
            # print(f"DEBUG: _parse_phone_string_direct: Early exit - phone_string_to_parse is empty.")
            return None

        effective_region = region or self.default_region
        print(f"DEBUG: _parse_phone_string_direct: Input='{phone_string_to_parse}', Region='{effective_region}'") # KEY DEBUG LINE

        try:
            num_obj = phonenumbers.parse(phone_string_to_parse, effective_region)
            is_valid = phonenumbers.is_valid_number(num_obj)
            print(f"DEBUG: _parse_phone_string_direct: Parsed='{num_obj}', IsValid={is_valid}") # KEY DEBUG LINE
            if is_valid:
                formatted = phonenumbers.format_number(num_obj, PhoneNumberFormat.E164)
                print(f"DEBUG: _parse_phone_string_direct: Formatted='{formatted}'") # KEY DEBUG LINE
                return formatted
        except NumberParseException as e:
            print(f"DEBUG: _parse_phone_string_direct: NumberParseException='{e}' for Input='{phone_string_to_parse}'") # KEY DEBUG LINE
            if not phone_string_to_parse.startswith('+'):
                print(f"DEBUG: _parse_phone_string_direct: Trying fallback parse (no region) for '{phone_string_to_parse}'") # KEY DEBUG LINE
                try:
                    num_obj_noregion = phonenumbers.parse(phone_string_to_parse, None)
                    is_valid_noregion = phonenumbers.is_valid_number(num_obj_noregion)
                    print(f"DEBUG: _parse_phone_string_direct: Fallback Parsed='{num_obj_noregion}', IsValid={is_valid_noregion}") # KEY DEBUG LINE
                    if is_valid_noregion:
                        formatted_noregion = phonenumbers.format_number(num_obj_noregion, PhoneNumberFormat.E164)
                        print(f"DEBUG: _parse_phone_string_direct: Fallback Formatted='{formatted_noregion}'") # KEY DEBUG LINE
                        return formatted_noregion
                except NumberParseException as e2:
                    print(f"DEBUG: _parse_phone_string_direct: Fallback NumberParseException='{e2}'") # KEY DEBUG LINE
        print(f"DEBUG: _parse_phone_string_direct: Returning None for Input='{phone_string_to_parse}'") # KEY DEBUG LINE
        return None
    
# In class HTMLScraper:
# In class HTMLScraper:

# In class HTMLScraper:

# In class HTMLScraper:

# In class HTMLScraper:

# In class HTMLScraper:

# In class HTMLScraper:

# In class HTMLScraper:

    def extract_phone_numbers(self) -> List[str]:
        if not phonenumbers:
            logger.warning("Phonenumbers library not available, cannot extract phone numbers.")
            return []
        unique_formatted_phones: Set[str] = set()

        # A. Prioritize tel: Links
        # ... (This part remains the same as the previous version in the Canvas)
        for link_tag in self.soup.select('a[href^="tel:"]'):
            href_attr = link_tag.get("href", "").replace("tel:", "").strip()
            phone_from_href = self._parse_phone_string_direct(href_attr, self.default_region)
            if phone_from_href:
                logger.debug(f"Phone from tel:href: '{href_attr}' -> '{phone_from_href}'")
                unique_formatted_phones.add(phone_from_href)
            else: 
                link_text = self._extract_text_content(link_tag)
                if link_text:
                    try:
                        for match in PhoneNumberMatcher(link_text, self.default_region, Leniency.POSSIBLE):
                            if phonenumbers.is_valid_number(match.number):
                                formatted_num = phonenumbers.format_number(match.number, PhoneNumberFormat.E164)
                                logger.debug(f"Phone from tel:link_text via Matcher: '{match.raw_string}' -> '{formatted_num}'")
                                unique_formatted_phones.add(formatted_num)
                    except Exception as e:
                        logger.trace(f"PhoneNumberMatcher error in tel: link text: {e} for text '{link_text[:100]}...'")
        
        # B. Targeted Text Blocks for PhoneNumberMatcher
        high_confidence_selectors = [
            '.phone-number', '.tel', '.contact-phone', '[itemprop="telephone"]',
        ]
        broader_context_selectors = [
            '.contact-info', '.contact', 'address', 'footer', 'header',
            '[class*="contact"]', '[id*="contact"]',
            '[class*="phone"]', '[id*="phone"]',
            'p', 'div', 'li', 'span', 'td' 
        ]
        
        elements_to_search = []
        for selector_list in [high_confidence_selectors, broader_context_selectors]:
            for selector in selector_list:
                try: elements_to_search.extend(self.soup.select(selector))
                except Exception as e: logger.trace(f"Selector error in phone extraction '{selector}': {e}")
        
        if not elements_to_search and self.soup.body:
            elements_to_search.append(self.soup.body)

        unique_elements_to_search_set = set()
        temp_unique_list = []
        for el in elements_to_search:
            if el not in unique_elements_to_search_set:
                temp_unique_list.append(el)
                unique_elements_to_search_set.add(el)
        elements_to_search = temp_unique_list

        processed_elements_text = set()

        for element in elements_to_search:
            is_inside_tel_link_text = False
            temp_parent = element
            while temp_parent:
                if temp_parent.name == 'a' and temp_parent.get('href','').startswith('tel:'):
                    is_inside_tel_link_text = True; break
                try: temp_parent = temp_parent.parent
                except AttributeError: temp_parent = None; break
            if is_inside_tel_link_text and element.name != 'a': continue

            block_text = self._extract_text_content(element)
            if not block_text or len(block_text) < 7: continue

            if len(block_text) > 200:
                 if block_text in processed_elements_text: continue
                 processed_elements_text.add(block_text)
            
            debug_this_block = False
            keywords_for_debug = [
                "1-800-GOOD-BOY", "1-800-TEST-EXT", "1-800-FAX-MEEE", 
                "1.800.GET.THIS", "FLOWERS", "Order ID", "987-654-3210",
                "5551112222", "555-222-3333", "5551234567", "555-456-7890"
            ]
            for keyword in keywords_for_debug:
                if keyword in block_text: debug_this_block = True; break
            
            if debug_this_block:
                print(f"\nDEBUG: extract_phone_numbers: ---- Processing Block for Potential Failing Case ----")
                element_class_list = element.get('class', [])
                element_class_str = ' '.join(element_class_list) if element_class_list else 'N/A'
                element_id = element.get('id', 'N/A')
                print(f"DEBUG: extract_phone_numbers: Element: <{element.name} class='{element_class_str}' id='{element_id}'>")
                print(f"DEBUG: extract_phone_numbers: Block Text for Matcher: '''{block_text}'''")
            
            match_found_in_this_block_for_debug_display = False
            any_valid_in_block_for_debug = False
            try:
                if debug_this_block:
                    print(f"DEBUG: extract_phone_numbers: Initializing PhoneNumberMatcher for block (Region: {self.default_region}, Leniency: POSSIBLE).")
                
                matcher_instance = PhoneNumberMatcher(block_text, self.default_region, Leniency.POSSIBLE)
                
                if debug_this_block:
                    print(f"DEBUG: extract_phone_numbers: Starting iteration over PhoneNumberMatcher results...")

                for match_index, match in enumerate(matcher_instance):
                    match_found_in_this_block_for_debug_display = True
                    is_currently_valid = phonenumbers.is_valid_number(match.number) # Check validity
                    
                    if debug_this_block:
                        print(f"DEBUG: extract_phone_numbers: Matcher Candidate ({match_index+1}): "
                              f"Raw='{match.raw_string}', NumberObj='{match.number}', IsValidDirectly={is_currently_valid}")
                    
                    if is_currently_valid: # Use the pre-checked validity
                        formatted_num = phonenumbers.format_number(match.number, PhoneNumberFormat.E164)
                        if debug_this_block:
                            print(f"DEBUG: extract_phone_numbers:   ↳ Valid & Formatted: '{formatted_num}'")
                        unique_formatted_phones.add(formatted_num)
                        any_valid_in_block_for_debug = True 
                
                if debug_this_block: 
                    if not match_found_in_this_block_for_debug_display:
                        print(f"DEBUG: extract_phone_numbers: NO CANDIDATES AT ALL yielded by PhoneNumberMatcher iterator for block: '''{block_text}'''")
                    elif not any_valid_in_block_for_debug: 
                        print(f"DEBUG: extract_phone_numbers: Candidates were found by Matcher, but NONE were deemed VALID for block: '''{block_text}'''")
                    elif any_valid_in_block_for_debug: 
                        print(f"DEBUG: extract_phone_numbers: At least one VALID number was processed by Matcher for block: '''{block_text}'''")
                    print(f"DEBUG: extract_phone_numbers: ---- Finished Processing Block ----\n")

            except Exception as e:
                if debug_this_block:
                    print(f"DEBUG: extract_phone_numbers: EXCEPTION during PhoneNumberMatcher processing for block: '''{block_text}'''. Error: {type(e).__name__} - {e}")
                    import traceback
                    print(traceback.format_exc())
                    print(f"DEBUG: extract_phone_numbers: ---- Finished Processing Block (due to exception) ----\n")

                if len(block_text) > 5000: 
                     logger.warning(f"PhoneNumberMatcher skipped very long text block ({len(block_text)} chars) from element '{element.name}'. Error (if any): {e}")
                else:
                     logger.trace(f"PhoneNumberMatcher error in general text block: {e} for text '{block_text[:100]}...' from element '{element.name}'")

        sorted_phones = sorted(list(unique_formatted_phones))
        logger.info(f"Found {len(sorted_phones)} unique phone number(s) for {self.source_url}: {sorted_phones}")
        return sorted_phones



    def extract_emails(self) -> List[str]:
        all_emails: Set[str] = set()

        # Cloudflare
        for link in self.soup.select('a[href^="/cdn-cgi/l/email-protection"]'):
            encoded_str = link.get('href', "")
            decoded_email = self._decode_cloudflare_email(encoded_str)
            if decoded_email:
                norm_email = normalize_email(decoded_email)
                if norm_email: all_emails.add(norm_email)
            
            link_text = self._extract_text_content(link) # Use new text extraction
            if link_text and "[email protected]" in link_text:
                 cf_match_text = re.search(r'#([a-f0-9]+)', link_text, re.IGNORECASE)
                 if cf_match_text:
                      decoded_from_text = self._decode_cloudflare_email(cf_match_text.group(1))
                      if decoded_from_text:
                           norm_email_text = normalize_email(decoded_from_text)
                           if norm_email_text: all_emails.add(norm_email_text)
        # Mailto links
        for link in self.soup.select('a[href^="mailto:"]'):
            href = link.get("href")
            if href:
                email_candidate = clean_text(href.replace("mailto:", "").split('?')[0])
                norm_email = normalize_email(email_candidate)
                if norm_email: all_emails.add(norm_email)
        
        # General text elements
        elements_for_email_search = self.soup.find_all(['p', 'div', 'span', 'li', 'td', 'address', 'footer', 'article', 'section'])
        if self.soup.body and not elements_for_email_search:
            elements_for_email_search.append(self.soup.body)

        processed_text_for_email = set()
        for element in elements_for_email_search:
            element_text = self._extract_text_content(element) # Use new text extraction
            if not element_text or len(element_text) < 5: continue

            if element_text in processed_text_for_email: continue
            processed_text_for_email.add(element_text)

            # De-obfuscation
            deobfuscated_text = element_text
            replacements = [
                (" [at] ", "@"), ("[at]", "@"), (" (at) ", "@"), ("(at)", "@"), (" AT ", "@"),(" at ", "@"),
                (" [dot] ", "."), ("[dot]", "."), (" (dot) ", "."), ("(dot)", "."), (" DOT ", "."), (" dot ", ".")
            ]
            for old, new in replacements:
                deobfuscated_text = deobfuscated_text.replace(old, new)
            
            # Handle HTML entities not converted by _extract_text_content (though it should handle most)
            deobfuscated_text = deobfuscated_text.replace("&#64;", "@").replace("&commat;", "@")
            deobfuscated_text = deobfuscated_text.replace("&#46;", ".").replace("&period;", ".")

            if "test@example.com" in deobfuscated_text.lower() and "also test@example.com" in deobfuscated_text.lower():
                 logger.trace(f"Email Regex Debug - Text: '{deobfuscated_text}'")
            
            emails_from_segment = extract_emails_from_text(deobfuscated_text) # from utils
            for email in emails_from_segment: # utils.extract_emails_from_text should already normalize
                all_emails.add(email)

        validated_emails_list: List[str] = []
        if validate_email:
            for email_str in all_emails:
                try:
                    # Ensure email is not overly long, which can be a DOS vector for some validators
                    if len(email_str) > 254: continue
                    email_info = validate_email(email_str, check_deliverability=False, allow_smtputf8=False)
                    validated_emails_list.append(email_info.normalized)
                except (EmailNotValidError if EmailNotValidError else Exception, ValueError): pass # type: ignore
            final_emails_list = sorted(list(set(validated_emails_list)))
        else:
            final_emails_list = sorted(list(all_emails))

        logger.info(f"Found {len(final_emails_list)} unique email address(es) for {self.source_url}: {final_emails_list}")
        return final_emails_list

    def _parse_address_with_library(self, address_text: str) -> Optional[Dict[str,str]]:
        if not address_text or not address_text.strip(): return None
        
        # Basic normalization here, _extract_text_content should have done most heavy lifting
        address_text_norm = clean_text(address_text)
        if not address_text_norm: return None

        expanded_address_texts = [address_text_norm] # Default if libpostal not available or fails
        if libpostal_expand_address_func:
            try:
                # libpostal_expand_address can return multiple variations
                expanded_address_texts = libpostal_expand_address_func(address_text_norm)
                if not expanded_address_texts: expanded_address_texts = [address_text_norm]
            except Exception as e:
                logger.debug(f"libpostal_expand_address error for '{address_text_norm}': {e}")
                expanded_address_texts = [address_text_norm]
        
        parsed_components: Optional[Dict[str, str]] = None
        
        if libpostal_parse_address_func:
            for text_to_parse in expanded_address_texts:
                if not text_to_parse or not text_to_parse.strip(): continue
                try:
                    parsed_tuples = libpostal_parse_address_func(text_to_parse)
                    temp_parsed_components = {key: value for value, key in parsed_tuples}
                    # Check for minimum viable components from libpostal
                    if sum(1 for k in ['road', 'house_number', 'city', 'postcode', 'state', 'country'] if k in temp_parsed_components and temp_parsed_components[k]) >= 2:
                        parsed_components = temp_parsed_components
                        logger.trace(f"Libpostal parsed: {parsed_components} from '{text_to_parse}'")
                        break # Found a good parse with libpostal
                except Exception as e:
                    logger.debug(f"Libpostal_parse_address error for '{text_to_parse}': {e}")
            if parsed_components and not (parsed_components.get('road') and (parsed_components.get('city') or parsed_components.get('postcode'))):
                 logger.trace(f"Libpostal result for '{address_text_norm}' seems sparse, clearing for potential usaddress fallback.")
                 parsed_components = None # Clear if too sparse

        # Determine if usaddress should be tried
        is_us_by_libpostal = parsed_components and parsed_components.get('country', '').lower() in ['us', 'usa', 'united states']
        looks_like_us_heuristic = bool(re.search(r'\b[A-Z]{2}\b', address_text_norm) and \
                                   re.search(r'\b\d{5}(?:-\d{4})?\b', address_text_norm))

        should_try_usaddress = False
        if usaddress_tag_func:
            if not libpostal_parse_address_func and looks_like_us_heuristic: # Libpostal not available
                should_try_usaddress = True
            elif libpostal_parse_address_func and not parsed_components and looks_like_us_heuristic: # Libpostal gave nothing
                should_try_usaddress = True
            elif parsed_components and not parsed_components.get('country') and looks_like_us_heuristic: # Libpostal gave no country
                should_try_usaddress = True
            elif is_us_by_libpostal and not (parsed_components.get('road') and (parsed_components.get('city') or parsed_components.get('postcode'))):
                 # Libpostal says US, but parse is too sparse (e.g. only country and postcode)
                 should_try_usaddress = True

        if should_try_usaddress:
            logger.trace(f"Attempting usaddress parsing for: '{address_text_norm}'")
            try:
                us_parsed_dict, address_type = usaddress_tag_func(address_text_norm)
                if us_parsed_dict.get('AddressNumber') and us_parsed_dict.get('StreetName') and (us_parsed_dict.get('PlaceName') or us_parsed_dict.get('ZipCode')):
                    mapped_us_components = {}
                    if us_parsed_dict.get('AddressNumber'): mapped_us_components['house_number'] = us_parsed_dict['AddressNumber']
                    street_parts = [us_parsed_dict.get('StreetNamePreDirectional'), us_parsed_dict.get('StreetName'), us_parsed_dict.get('StreetNamePostType'), us_parsed_dict.get('StreetNamePostDirectional')]
                    mapped_us_components['road'] = " ".join(filter(None, street_parts)).strip() or None
                    
                    unit_parts = [us_parsed_dict.get('OccupancyType'), us_parsed_dict.get('OccupancyIdentifier')]
                    mapped_us_components['unit'] = " ".join(filter(None, unit_parts)).strip() or None
                    
                    if us_parsed_dict.get('PlaceName'): mapped_us_components['city'] = us_parsed_dict['PlaceName']
                    if us_parsed_dict.get('StateName'): mapped_us_components['state'] = us_parsed_dict['StateName']
                    if us_parsed_dict.get('ZipCode'): mapped_us_components['postcode'] = us_parsed_dict['ZipCode']
                    mapped_us_components['country'] = 'US' # usaddress implies US
                    
                    # If usaddress provides a more complete US parse, prefer it.
                    if mapped_us_components.get('road') and (mapped_us_components.get('city') or mapped_us_components.get('postcode')):
                        logger.debug(f"usaddress provided a better/sufficient parse: {mapped_us_components}")
                        return mapped_us_components # Return directly
                else:
                    logger.trace(f"usaddress parse for '{address_text_norm}' was too sparse.")
            except (USAddressRepeatedLabelError if USAddressRepeatedLabelError else Exception, ValueError, IndexError) as e:
                 logger.trace(f"usaddress tagging error for '{address_text_norm}': {e}")
        
        return parsed_components # Return libpostal result (which could be None)

    def _format_parsed_address(self, parsed_address: Dict[str, str]) -> Optional[str]:
        if not parsed_address: return None
        
        # Ensure essential components like road and city/postcode are present
        if not (parsed_address.get('road') and (parsed_address.get('city') or parsed_address.get('postcode'))):
            return None

        address_parts = []
        # Line 1: House number, road, unit
        line1_components = [parsed_address.get('house_number'), parsed_address.get('road')]
        line1 = " ".join(filter(None, line1_components)).strip()
        if parsed_address.get('unit'):
            line1 = f"{line1} {parsed_address['unit']}".strip()
        if line1: address_parts.append(line1)

        # City, State, Postcode, Country
        # Try to use more specific components if 'city' or 'state' is missing but sub-components exist
        city_str = parsed_address.get('city')
        if not city_str:
            city_alt_parts = [parsed_address.get('suburb'), parsed_address.get('city_district')]
            city_str = " ".join(filter(None, city_alt_parts)).strip() or None
        
        state_str = parsed_address.get('state')
        if not state_str and parsed_address.get('state_district'):
            state_str = parsed_address.get('state_district')
        
        postcode_str = parsed_address.get('postcode')
        country_str = parsed_address.get('country')

        # Construct locality line (City, State Postcode)
        locality_parts = []
        if city_str: locality_parts.append(city_str)
        
        state_zip_parts = []
        if state_str: state_zip_parts.append(state_str)
        if postcode_str: state_zip_parts.append(postcode_str)
        if state_zip_parts: locality_parts.append(" ".join(state_zip_parts))
        
        if locality_parts: address_parts.append(", ".join(filter(None, locality_parts)))
        
        if country_str and country_str.upper() not in ['US', 'USA'] : # Add country if not US (US often omitted in US addresses)
             if address_parts and city_str and not state_str and not postcode_str: # e.g. "Paris, France"
                  address_parts[-1] = f"{address_parts[-1]}, {country_str}"
             elif country_str:
                  address_parts.append(country_str)
        
        final_address = ", ".join(filter(None, address_parts))
        return final_address if final_address and len(final_address.split(',')) >=2 else None


    def extract_addresses(self) -> List[str]:
        found_addresses_set: Set[str] = set()

        # Schema.org PostalAddress
        for elem in self.soup.find_all(itemscope=True, itemtype=lambda x: x and "PostalAddress" in x):
            address_block_text = self._extract_text_content(elem)
            if address_block_text and 10 <= len(address_block_text) <= 500:
                parsed_components = self._parse_address_with_library(address_block_text)
                if parsed_components:
                    formatted_addr = self._format_parsed_address(parsed_components)
                    if formatted_addr:
                        found_addresses_set.add(formatted_addr)
                        continue # Successfully processed this schema element
            
            # Fallback: build from itemprops if block parse failed
            schema_parts = {prop: self._extract_text_content(item)
                            for prop in ["name", "streetAddress", "postOfficeBoxNumber", "addressLocality", "addressRegion", "postalCode", "addressCountry"]
                            if (item := elem.find(itemprop=prop))}
            if schema_parts.get("streetAddress") and schema_parts.get("addressLocality"):
                constructed_addr_str = ", ".join(filter(None, [
                    schema_parts.get("name"), schema_parts.get("streetAddress") or schema_parts.get("postOfficeBoxNumber"),
                    schema_parts.get("addressLocality"), schema_parts.get("addressRegion"),
                    schema_parts.get("postalCode"), schema_parts.get("addressCountry")]))
                if constructed_addr_str:
                    parsed_comps_fallback = self._parse_address_with_library(constructed_addr_str)
                    if parsed_comps_fallback:
                        formatted_fallback = self._format_parsed_address(parsed_comps_fallback)
                        if formatted_fallback: found_addresses_set.add(formatted_fallback)
        
        # Heuristic Search
        container_selectors = [
            'address', '.address', '.location', '[class*="addr"]', '[id*="addr"]', 'footer',
            '.contact-info', '.contact-details', '.widget_contact_info',
            'div[itemtype="http://schema.org/Organization"]' # Organization sometimes contains address text
        ]
        candidate_elements = {el for selector in container_selectors for el in self.soup.select(selector)
                              if not (el.get("itemscope") and "PostalAddress" in el.get("itemtype", ""))} # Avoid re-processing schema

        if not candidate_elements and self.soup.body:
            body_text = self._extract_text_content(self.soup.body)
            if body_text: # Split body text into address-like chunks
                for chunk in re.split(r'\n\s*\n', body_text): # Split by blank lines
                    chunk = chunk.strip()
                    if 15 < len(chunk) < 400:
                        parsed = self._parse_address_with_library(chunk)
                        if parsed:
                            formatted = self._format_parsed_address(parsed)
                            if formatted: found_addresses_set.add(formatted)
        else:
            for container in candidate_elements:
                container_text = self._extract_text_content(container)
                if not container_text or not (15 < len(container_text) < 600): continue

                # Attempt to parse segments of the container text
                # Split by multiple newlines or patterns that suggest distinct address blocks
                potential_address_segments = re.split(r'\n\s*\n+|(?<=\d)\s*\n(?=[A-Z])', container_text)
                if not potential_address_segments or len(potential_address_segments) == 1 and potential_address_segments[0] == container_text:
                     potential_address_segments = [container_text] # Process as a whole if no clear splits

                for segment in potential_address_segments:
                    segment = segment.strip()
                    if not (15 < len(segment) < 400): continue
                    
                    is_redundant = any(segment in addr for addr in found_addresses_set) or \
                                   any(addr in segment for addr in found_addresses_set if len(addr) > len(segment) * 0.7)
                    if is_redundant: continue

                    parsed = self._parse_address_with_library(segment)
                    if parsed:
                        formatted = self._format_parsed_address(parsed)
                        if formatted: found_addresses_set.add(formatted)
        
        final_list = sorted([addr for addr in list(found_addresses_set) if addr]) # Ensure no None/empty strings
        logger.info(f"Found {len(final_list)} unique address(es) for {self.source_url}: {final_list}")
        return final_list

    def extract_social_media_links(self) -> Dict[str, str]:
        social_links: Dict[str, str] = {}
        processed_urls: Set[str] = set()

        for link_tag in self.soup.find_all("a", href=True):
            href = link_tag.get("href")
            if not href: continue
            
            abs_href = make_absolute_url(self.source_url, href)
            if not abs_href or abs_href in processed_urls: continue
            processed_urls.add(abs_href)

            try:
                parsed_link = urlparse(abs_href)
                netloc = parsed_link.netloc.lower().replace("www.", "")
                path_full = parsed_link.path.strip('/')
                query_params = parsed_link.query
            except Exception: continue

            for platform_key, platform_info in SOCIAL_MEDIA_PLATFORMS.items():
                if platform_key in social_links: continue # Already found one for this platform
                        
                # 1. Domain Match
                is_domain_match = (platform_info["domain"] == netloc or netloc in platform_info.get("alt_domains", []))
                if not is_domain_match: continue

                # 2. Check Exclusions (applied to full path)
                if "path_exclusions" in platform_info:
                    if any(ex_pattern in path_full for ex_pattern in platform_info["path_exclusions"]):
                        continue # Excluded path

                is_valid_by_path = False
                # 3. Check Prefixes (strong positive signal)
                if "path_prefixes" in platform_info:
                    for prefix in platform_info["path_prefixes"]:
                        if path_full.startswith(prefix.strip('/')): # Match prefix at start of path
                            # Check if there's content after prefix or if prefix itself is enough
                            # e.g. linkedin.com/company/ is not enough, but linkedin.com/company/name is.
                            # A simple check: path must be longer than the prefix (unless prefix is the entire valid path)
                            if len(path_full) > len(prefix.strip('/')) or platform_info.get("prefix_is_full_path", False):
                                is_valid_by_path = True
                                break
                
                # 4. Check Path Regex (if no prefix matched and validated, or if regex is a general rule)
                if not is_valid_by_path and "path_regex" in platform_info:
                    # Apply regex to the first significant path segment
                    # For TikTok, ensure @ is present if regex expects it
                    first_segment = path_full.split('/')[0] if path_full else ""
                    segment_for_regex = first_segment
                    if platform_key == "tiktok" and first_segment and not first_segment.startswith("@"):
                        segment_for_regex = f"@{first_segment}"
                    
                    if re.fullmatch(platform_info["path_regex"], segment_for_regex): # Use fullmatch for segment
                        is_valid_by_path = True
                
                # If no prefixes are defined, rely solely on regex (if defined) or domain match only if no path validation needed
                elif "path_prefixes" not in platform_info and "path_regex" not in platform_info:
                    if not path_full or platform_info.get("allow_empty_path", False): # e.g. some base domains are enough
                        is_valid_by_path = True


                # 5. Special Cases (e.g., Facebook profile.php)
                if not is_valid_by_path and platform_key == "facebook" and \
                   platform_info.get("profile_php") and platform_info["profile_php"] in path_full:
                    if "id=" in query_params:
                        is_valid_by_path = True
                
                if is_valid_by_path:
                    social_links[platform_key] = abs_href
                    logger.debug(f"Found social media ({platform_key}): {abs_href}")
                    break # Move to next link_tag
        
        logger.info(f"Found {len(social_links)} social media link(s) for {self.source_url}.")
        return social_links

    def extract_description(self) -> Optional[str]:
        tags_to_check = [
            {"name": "description"}, {"property": "og:description"}, {"name": "twitter:description"}
        ]
        for attrs in tags_to_check:
            meta_tag = self.soup.find("meta", attrs=attrs)
            if meta_tag and meta_tag.get("content"):
                description = clean_text(meta_tag["content"])
                if description: return description
        return None
        
    def extract_canonical_url(self) -> Optional[str]:
        canonical_link = self.soup.find("link", rel="canonical")
        if canonical_link and canonical_link.get("href"):
            return make_absolute_url(self.source_url, canonical_link["href"])
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

        main_website = None
        if self.scraped_data["canonical_url"]:
            try:
                parsed_canonical = urlparse(self.scraped_data["canonical_url"])
                if parsed_canonical.scheme and parsed_canonical.netloc:
                    main_website = f"{parsed_canonical.scheme}://{parsed_canonical.netloc}"
            except Exception: pass # Ignore malformed canonical URLs
        if not main_website:
            try:
                parsed_source = urlparse(self.source_url)
                if parsed_source.scheme and parsed_source.netloc:
                    main_website = f"{parsed_source.scheme}://{parsed_source.netloc}"
            except Exception: pass # Ignore malformed source_url
        self.scraped_data["website"] = main_website
        
        extracted_summary = {k:v for k,v in self.scraped_data.items() if v or isinstance(v, (list, dict)) and v} # Check if value is truthy or a non-empty list/dict
        logger.success(f"Scraping complete for {self.source_url}. Extracted fields: {list(extracted_summary.keys())}")
        return self.scraped_data

if __name__ == '__main__':
    # Example usage:
    sample_html_complex = """
    <html><head>
        <title>Complex Solutions Ltd. | Innovative Tech</title>
        <meta property="og:site_name" content="Complex Solutions Ltd">
        <meta name="description" content="Leading provider of tech solutions. Contact us for more info.">
        <link rel="canonical" href="https://www.complexsolutions.com/home">
    </head><body>
        <h1>Welcome to Complex Solutions Ltd.</h1>
        <p>Call us: 1-800-COMPLEX. Email: <a href="mailto:info@complexsolutions.com">info@complexsolutions.com</a> or contact [at] complexsolutions [dot] com.</p>
        <p>Our main line is (555) 123-4567. UK: +44 207 123 4567. Fax (US): 1-888-FAX-THIS.</p>
        <div class="contact-section">
            <address itemscope itemtype="http://schema.org/PostalAddress">
                <span itemprop="name">HQ</span>:
                <span itemprop="streetAddress">123 Innovation Drive</span>,
                <span itemprop="addressLocality">Techville</span>,
                <span itemprop="addressRegion">CA</span> <span itemprop="postalCode">90210</span>,
                <span itemprop="addressCountry">USA</span>.
            </address>
            <p>European Office: 45 Business Park, Dublin D02 XW77, Ireland</p>
        </div>
        <div class="social">
            <a href="https://www.linkedin.com/company/complex-solutions-ltd">LinkedIn</a>
            <a href="http://twitter.com/complexsol">Twitter</a>
            <a href="https://facebook.com/complexsolutionsltd">Facebook</a>
            <a href="youtube.com/c/ComplexSolutionsVideo">YouTube</a>
            <a href="https://www.tiktok.com/@complexdata">TikTok</a>
        </div>
        <footer>Copyright 2024 Complex Solutions Limited. Office: 1-800-NEW-DEAL.</footer>
    </body></html>"""
    scraper = HTMLScraper(sample_html_complex, "https://www.complexsolutions.com")
    data = scraper.scrape()
    import json
    print(json.dumps(data, indent=4))

    # Test with email case from tests
    email_test_html = "<p>Email: test@example.com. Also TEST@EXAMPLE.COM.</p>"
    email_scraper = HTMLScraper(email_test_html, "http://emailtest.com")
    email_data = email_scraper.extract_emails()
    print(f"\nEmail test result: {email_data}") # Expected: ['test@example.com']

    # Test phone cases from tests
    phone_test_html_1 = "<a href='tel:ignoreme'>Call 555-222-3333</a>"
    phone_scraper_1 = HTMLScraper(phone_test_html_1, "http://phonetest1.com")
    phone_data_1 = phone_scraper_1.extract_phone_numbers()
    print(f"\nPhone test 1 ('tel:ignoreme' text): {phone_data_1}") # Expected: ['+15552223333']

    phone_test_html_2 = "Phone: <span>1-800</span>-<span>FLOWERS</span>"
    phone_scraper_2 = HTMLScraper(phone_test_html_2, "http://phonetest2.com")
    phone_data_2 = phone_scraper_2.extract_phone_numbers()
    print(f"\nPhone test 2 (split span vanity): {phone_data_2}") # Expected: ['+18003569377']

    address_test_html_1 = """<div itemprop itemtype="http://schema.org/PostalAddress">
          <span itemprop="streetAddress">123 Main St</span>,
          <span itemprop="addressLocality">Anytown</span>, CA
       </div>"""
    address_scraper_1 = HTMLScraper(address_test_html_1, "http://addresstest1.com")
    address_data_1 = address_scraper_1.extract_addresses()
    print(f"\nAddress test 1 (schema): {address_data_1}")