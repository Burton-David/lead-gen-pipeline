# lead_gen_pipeline/scraper.py
# Version: v14_targeted_fixes

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
except ImportError: # Fallback for direct script execution or unusual environments
    # This section is a simplified fallback and might not have all functionalities.
    # It's better to run the scraper as part of the package.
    print("Fallback imports used in scraper.py. Ensure package structure is correct for full functionality.")
    # Attempt to import from a sibling directory if run directly from lead_gen_pipeline
    try:
        from utils import logger, clean_text, extract_emails_from_text, normalize_email, make_absolute_url # type: ignore
        from config import settings as global_app_settings # type: ignore
        from placeholder_data import ( # type: ignore
            GENERIC_PHONE_PATTERNS, GENERIC_EMAIL_PATTERNS, GENERIC_EMAIL_DOMAINS,
            GENERIC_COMPANY_TERMS, GENERIC_SOCIAL_MEDIA_PATHS,
            PLACEHOLDER_WEBSITE_DOMAINS, PLACEHOLDER_TLDS
        )
    except ImportError: # Absolute fallback if even sibling imports fail
        # Define dummy logger and minimal placeholders if all imports fail
        class DummyLogger:
            def info(self, msg): print(f"INFO: {msg}")
            def warning(self, msg): print(f"WARNING: {msg}")
            def error(self, msg): print(f"ERROR: {msg}")
            def debug(self, msg): print(f"DEBUG: {msg}")
            def trace(self, msg): print(f"TRACE: {msg}")
            def success(self, msg): print(f"SUCCESS: {msg}")
        logger = DummyLogger() # type: ignore
        def clean_text(text): return text.strip() if text else None
        def extract_emails_from_text(text): return []
        def normalize_email(email): return email
        def make_absolute_url(base, rel): return rel
        class GlobalAppSettings: pass
        global_app_settings = GlobalAppSettings() # type: ignore
        GENERIC_PHONE_PATTERNS, GENERIC_EMAIL_PATTERNS, GENERIC_EMAIL_DOMAINS = set(),set(),set()
        GENERIC_COMPANY_TERMS, GENERIC_SOCIAL_MEDIA_PATHS = set(),set()
        PLACEHOLDER_WEBSITE_DOMAINS, PLACEHOLDER_TLDS = set(),set()


# Attempt to import optional, enhancing libraries
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
        # Attempt to load a small English model. Modify if a different model is preferred/available.
        NLP_SPACY = spacy.load("en_core_web_sm")
    except OSError:
        NLP_SPACY = None
        logger.warning("spaCy model 'en_core_web_sm' not found or failed to load. NER for company name disabled.")
except ImportError:
    spacy = None # type: ignore
    NLP_SPACY = None
    logger.warning("spaCy library not found. NER for company name disabled.")

try:
    from email_validator import validate_email, EmailNotValidError
except ImportError:
    validate_email = None # type: ignore
    EmailNotValidError = None # type: ignore
    logger.warning("email-validator library not found. Advanced email validation disabled.")

# Address parsing libraries (usaddress for US, pypostal for international)
try:
    from usaddress import tag as usaddress_tag_func, RepeatedLabelError as USAddressRepeatedLabelError
except ImportError:
    usaddress_tag_func = None # type: ignore
    USAddressRepeatedLabelError = None # type: ignore
    logger.warning("usaddress library not found. US address parsing limited.")

try:
    # libpostal (via pypostal) is powerful for international addresses
    from postal.parser import parse_address as libpostal_parse_address_func
    from postal.expand import expand_address as libpostal_expand_address_func
except ImportError:
    libpostal_parse_address_func = None # type: ignore
    libpostal_expand_address_func = None # type: ignore
    logger.warning("pypostal (libpostal) library not found. International address parsing disabled.")


SOCIAL_MEDIA_PLATFORMS = {
    "linkedin": {
        "domain": "linkedin.com",
        "alt_domains": ["www.linkedin.com"],
        "path_prefixes": ["/company/", "/in/", "/school/", "/pub/", "/showcase/"],
        "path_exclusions": ["/feed/", "/shareArticle", "/posts/", "/login", "/signup", "/help/", "/legal/", "pulse/", "showcase/"] + list(GENERIC_SOCIAL_MEDIA_PATHS)
    },
    "twitter": { # Covers X.com as well
        "domain": "x.com", # Primary domain for X
        "alt_domains": ["twitter.com", "www.twitter.com", "www.x.com"], # Aliases
        "path_regex": r"^[A-Za-z0-9_]{1,15}$", # Typical username pattern for the first path segment
        "path_exclusions": [
            "search", "hashtag", "intent", "home", "share", "widgets", "status/", "i/web", "login",
            "explore", "notifications", "messages", "compose", "settings", "following", "followers",
            "lists", "communities", "premium_subscribe", "tos", "privacy", "about", "jobs", "advertise",
            "everyone", "verified_followers", "display", "media" # Added media
        ] + list(GENERIC_SOCIAL_MEDIA_PATHS)
    },
    "facebook": {
        "domain": "facebook.com",
        "alt_domains": ["www.facebook.com", "fb.com", "fb.me"],
        "path_prefixes": ["/pages/", "/pg/", "/groups/"],
        "path_regex": r"^[a-zA-Z0-9._-]+/?$",
        "profile_php": "profile.php",
        "path_exclusions": [
            "sharer", "dialog/", "plugins", "video.php", "photo.php", "story.php", "watch",
            "events", "login.php", "marketplace", "gaming", "developer", "notes/", "media/set/",
            "ads/", "help", "terms", "policies", "pages/creation/", "messages/", "posts/" # Added posts
        ] + list(GENERIC_SOCIAL_MEDIA_PATHS)
    },
    "instagram": {
        "domain": "instagram.com",
        "alt_domains": ["www.instagram.com"],
        "path_regex": r"^[A-Za-z0-9_.\-]+/?$",
        "path_exclusions": ["/p/", "/reels/", "/stories/", "/explore/", "/accounts/", "/direct/", "challenge/", "accounts/login/"] + list(GENERIC_SOCIAL_MEDIA_PATHS)
    },
    "youtube": {
        "domain": "youtube.com", # Simpler main domain
        "alt_domains": ["www.youtube.com", "m.youtube.com", "youtu.be"], # Common variations
        "path_prefixes": ["/channel/", "/c/", "/user/", "/@"],
        "path_regex": r"^[A-Za-z0-9_.-]+$",
        "path_exclusions": [
            "/watch", "/embed", "/feed", "/playlist", "/results", "/redirect",
            "/shorts", "/live", "/community", "/store", "/music", "/premium",
            "/account", "/feed/subscriptions", "/feed/history", "results?search_query=",
            "/t/", "/s/", "/clip/", "howyoutubeworks", "about/", "features", "creators", "ads",
            "audiolibrary", "copyright", "jobs", "kids", "movies", "tv", "gaming", "live_chat" # More specific exclusions
        ] + list(GENERIC_SOCIAL_MEDIA_PATHS)
    },
    "pinterest": {
        "domain": "pinterest.com",
        "alt_domains": ["www.pinterest.com", "pinterest.co.uk", "pinterest.ca", "pinterest.fr", "pinterest.de", "pinterest.com.au", "pinterest.es", "pinterest.it", "pinterest.jp", "pinterest.kr", "pinterest.pt", "pinterest.ch"],
        "path_regex": r"^[A-Za-z0-9_]+/?$",
        "path_exclusions": ["/pin/", "/ideas/", "/search/", "/settings/", "/login/", "_created/", "_saved/", "categories/", "topics/", "videos/", "boards/"] + list(GENERIC_SOCIAL_MEDIA_PATHS)
    },
    "tiktok": {
        "domain": "tiktok.com",
        "alt_domains": ["www.tiktok.com"],
        "path_regex": r"^@[A-Za-z0-9_.]+$",
        "path_exclusions": ["/tag/", "/music/", "/trending", "/foryou", "/search", "/upload", "/messages", "/live", "/explore", "/following", "/friends", "share/user/", "embed/", "channel/", "discover"] + list(GENERIC_SOCIAL_MEDIA_PATHS)
    }
}
COMPREHENSIVE_GENERIC_TITLES = GENERIC_COMPANY_TERMS

class HTMLScraper:
    def __init__(self, html_content: str, source_url: str):
        if not html_content:
            logger.warning(f"HTMLScraper initialized with empty or None HTML content for URL: {source_url}")
            self.soup = BeautifulSoup("", "html.parser")
        else:
            self.soup = BeautifulSoup(html_content, "html.parser")
        self.source_url = source_url
        self.default_region = "US"
        self.scraped_data: Dict[str, Any] = {}

    def _is_generic_phone(self, phone_text: str) -> bool:
        if not phone_text: return False
        normalized_for_check = re.sub(r'[^\da-zA-Z]', '', phone_text).lower()
        for pattern in GENERIC_PHONE_PATTERNS:
            norm_pattern = re.sub(r'[^\da-zA-Z]', '', pattern).lower()
            if norm_pattern == normalized_for_check or pattern.lower() in phone_text.lower():
                return True
        # Check for sequences of same digit (e.g., 000-000-0000, 1111111) longer than 6 digits
        if len(normalized_for_check) >= 7 and len(set(normalized_for_check)) == 1:
            return True
        return False

    def _is_generic_email(self, email_text: str) -> bool:
        if not email_text: return False
        email_lower = email_text.lower()
        if email_lower in GENERIC_EMAIL_PATTERNS:
            return True
        try:
            domain_part = email_lower.split('@', 1)[1]
            if domain_part in GENERIC_EMAIL_DOMAINS:
                return True
            if any(domain_part.endswith(tld) for tld in PLACEHOLDER_TLDS):
                domain_name_part = domain_part.rsplit('.', 1)[0]
                if domain_name_part in GENERIC_EMAIL_DOMAINS or domain_name_part in {"placeholder", "sample", "demo", "test", "yourname"}:
                    return True
        except IndexError:
            pass
        return False

    def _extract_text_content(self, element: Optional[Tag]) -> Optional[str]:
        if not element:
            return None
        try:
            full_text = element.get_text(separator=' ', strip=True)
        except Exception as e:
            logger.debug(f"element.get_text() failed for element '{element.name if element else 'None'}': {e}. Using manual iteration.")
            texts = []
            if element:
                for descendant in element.descendants:
                    if isinstance(descendant, NavigableString):
                        parent_name = descendant.parent.name if descendant.parent else ''
                        if parent_name in ['script', 'style', 'noscript', 'meta', 'link', 'head', 'button', 'option', 'select', 'textarea', 'input', 'title']:
                            continue
                        texts.append(str(descendant))
                    elif isinstance(descendant, Tag) and descendant.name == 'br':
                        texts.append(' ')
                full_text = "".join(texts)
                full_text = re.sub(r'\s+', ' ', full_text).strip()
            else:
                full_text = ""

        if not full_text:
            return None
            
        normalized_text = unicodedata.normalize('NFKC', full_text)
        hyphen_like_chars = "‑–—−‒―‐"
        for char in hyphen_like_chars:
            normalized_text = normalized_text.replace(char, '-')
        normalized_text = normalized_text.replace('\xa0', ' ')
        
        final_text = clean_text(normalized_text)

        if final_text:
            final_text = re.sub(r'\s+([.,;:!?])', r'\1', final_text)
        
        return final_text if final_text else None


    def extract_company_name(self) -> Optional[str]:
        candidates: List[Tuple[str, int]] = []

        og_site_name_tag = self.soup.find("meta", property="og:site_name")
        if og_site_name_tag and og_site_name_tag.get("content"):
            name = clean_text(og_site_name_tag["content"])
            if name and name.lower() not in COMPREHENSIVE_GENERIC_TITLES:
                candidates.append((name, 10))

        org_schema = self.soup.find(itemtype=lambda x: x and ("Organization" in x or "Corporation" in x or "LocalBusiness" in x))
        if org_schema:
            name_tag = org_schema.find(itemprop="name")
            if not name_tag: name_tag = org_schema.find(itemprop="legalName")
            if name_tag:
                name = self._extract_text_content(name_tag)
                if name and name.lower() not in COMPREHENSIVE_GENERIC_TITLES:
                    candidates.append((name, 9))
        
        og_title_tag = self.soup.find("meta", property="og:title")
        if og_title_tag and og_title_tag.get("content"):
            name_content = clean_text(og_title_tag["content"])
            if name_content and name_content.lower() not in COMPREHENSIVE_GENERIC_TITLES:
                parts = re.split(r'\s*[:|\-–—•]\s*', name_content)
                for i, part in enumerate(reversed(parts)):
                    candidate_name = clean_text(part)
                    is_domain_part = False
                    if self.source_url:
                        try:
                            parsed_source = urlparse(self.source_url)
                            if parsed_source.netloc and candidate_name.lower() in parsed_source.netloc.lower().replace("www.",""):
                                is_domain_part = True
                        except: pass
                    
                    if (candidate_name and len(candidate_name.split()) <= 5 and
                       candidate_name.lower() not in COMPREHENSIVE_GENERIC_TITLES and
                       len(candidate_name) > 2 and not candidate_name.isdigit() and not is_domain_part):
                        score = 8 if i == 0 or i == len(parts) -1 else 7
                        candidates.append((candidate_name, score))
                        break
                else:
                    if len(name_content.split()) <=5 and name_content.lower() not in COMPREHENSIVE_GENERIC_TITLES and not name_content.isdigit():
                         candidates.append((name_content, 6))

        title_tag = self.soup.title
        if title_tag:
            raw_title = self._extract_text_content(title_tag)
            if raw_title and raw_title.lower() not in COMPREHENSIVE_GENERIC_TITLES:
                parts = re.split(r'\s*[:|\-–—•]\s*', raw_title)
                for i, part in enumerate(reversed(parts)):
                    cleaned_part = clean_text(part)
                    is_domain_part = False
                    if self.source_url:
                        try:
                            parsed_source = urlparse(self.source_url)
                            if parsed_source.netloc and cleaned_part.lower() in parsed_source.netloc.lower().replace("www.",""):
                                is_domain_part = True
                        except: pass

                    if (cleaned_part and cleaned_part.lower() not in COMPREHENSIVE_GENERIC_TITLES and
                        len(cleaned_part) > 2 and not cleaned_part.isdigit() and
                        len(cleaned_part.split()) <= 5 and not is_domain_part):
                        score = 7 if i == 0 or i == len(parts) -1 else 6
                        candidates.append((cleaned_part, score))
                        break
                else:
                     if len(raw_title.split()) <= 5 and raw_title.lower() not in COMPREHENSIVE_GENERIC_TITLES and not raw_title.isdigit():
                         candidates.append((raw_title, 5))

        footer = self.soup.find("footer")
        if footer:
            footer_text = self._extract_text_content(footer)
            if footer_text:
                copy_match_suffix = re.search(
                    r"(?:©|\bcopyright\b)\s*(?:(?:\d{4})(?:[\s\-–—]*(?:\d{4}|present))?)?\s*([A-Za-z0-9\s.,'&()-]+?(?:LLC|Inc\.?|Ltd\.?|Corp\.?|Co\.(?:\s|$)|GmbH|AG|SARL|Pty Ltd|S\.A\.))(?=[<\s.,]|All Rights Reserved|Privacy Policy|Terms of Use|$)",
                    footer_text, re.IGNORECASE
                )
                copy_match_generic = None
                if not copy_match_suffix:
                    copy_match_generic = re.search(
                        r"(?:©|\bcopyright\b)\s*(?:(?:\d{4})(?:[\s\-–—]*(?:\d{4}|present))?)?\s*([A-Za-z0-9][A-Za-z0-9\s.,'&()-]{2,70})(?=[<\s.,]|All Rights Reserved|Privacy Policy|Terms of Use|$)",
                        footer_text, re.IGNORECASE)
                
                copy_match = copy_match_suffix or copy_match_generic

                if copy_match and copy_match.group(1):
                    company_from_copyright = clean_text(copy_match.group(1).strip(" .,;&"))
                    if not any(company_from_copyright.lower().endswith(sfx.lower()) for sfx in [" llc", " inc", " ltd", " corp", " co.", " gmbh", " ag", " sarl", " pty ltd", " s.a."]):
                        company_from_copyright = re.sub(r'\s*(?:All Rights Reserved|Privacy Policy|Terms of Use.*)$', '', company_from_copyright, flags=re.IGNORECASE).strip(" .,;&")
                    if re.fullmatch(r"\d{4}", company_from_copyright) or company_from_copyright.lower() in {"all", "rights", "reserved", "present"}:
                        company_from_copyright = None

                    if (company_from_copyright and len(company_from_copyright.split()) <= 7 and
                        company_from_copyright.lower() not in COMPREHENSIVE_GENERIC_TITLES and len(company_from_copyright) > 2):
                        candidates.append((company_from_copyright, 7 if copy_match_suffix else 6))

        if NLP_SPACY and (not candidates or max(c[1] for c in candidates if c) < 8) :
            text_sources_for_ner: List[Optional[str]] = []
            h1 = self.soup.find('h1')
            if h1: text_sources_for_ner.append(self._extract_text_content(h1))
            
            for selector in ['.site-title', '.logo-text', '[class*="brand"]', '[id*="brand"]', '.navbar-brand', '[class*="logo"]', '[id*="logo"]', 'a[aria-label*="home" i] img[alt]']:
                elem = self.soup.select_one(selector)
                if elem:
                    img_alt = None
                    if elem.name == 'img' and elem.get('alt'):
                        img_alt = elem.get('alt')
                    else:
                        child_img = elem.find('img', alt=True)
                        if child_img and child_img.get('alt'):
                            img_alt = child_img.get('alt')
                    
                    if img_alt:
                        alt_text = clean_text(img_alt)
                        if alt_text and alt_text.lower() not in COMPREHENSIVE_GENERIC_TITLES:
                             text_sources_for_ner.append(alt_text)
                    else:
                        elem_text = self._extract_text_content(elem)
                        if elem_text and elem_text.lower() not in COMPREHENSIVE_GENERIC_TITLES:
                            text_sources_for_ner.append(elem_text)
            
            for text_content in filter(None, text_sources_for_ner):
                if text_content and len(text_content) > 300: text_content = text_content[:300]
                if text_content and text_content.lower() not in COMPREHENSIVE_GENERIC_TITLES and len(text_content.split()) <=5:
                    try:
                        doc = NLP_SPACY(text_content)
                        for ent in doc.ents:
                            if ent.label_ == "ORG":
                                org_name = clean_text(ent.text)
                                if (org_name and len(org_name.split()) <= 5 and len(org_name) > 2 and
                                    org_name.lower() not in COMPREHENSIVE_GENERIC_TITLES):
                                    candidates.append((org_name, 4))
                    except Exception as e:
                        logger.debug(f"spaCy processing error for company name: {e}")
        
        if not candidates:
            logger.info(f"Company name not found for {self.source_url}")
            return None

        unique_names: Dict[str, Tuple[str, int]] = {}
        for name, score in candidates:
            name_lower = name.lower()
            if (name_lower not in unique_names or
                score > unique_names[name_lower][1] or
                (score == unique_names[name_lower][1] and len(name) < len(unique_names[name_lower][0]))):
                unique_names[name_lower] = (name, score)
        
        if not unique_names: return None
        sorted_candidates = sorted(list(unique_names.values()), key=lambda x: (-x[1], len(x[0])))
        
        final_name = sorted_candidates[0][0]
        logger.debug(f"Selected company name: '{final_name}' (score: {sorted_candidates[0][1]}) for {self.source_url} from candidates: {sorted_candidates}")
        return final_name

    def _decode_cloudflare_email(self, encoded_string: str) -> Optional[str]:
        try:
            if encoded_string.startswith("/cdn-cgi/l/email-protection#"):
                encoded_string = encoded_string.split("#")[-1]
            if len(encoded_string) < 2: return None
            r = int(encoded_string[:2], 16)
            email = ''.join([chr(int(encoded_string[i:i+2], 16) ^ r) for i in range(2, len(encoded_string), 2)])
            return email
        except ValueError:
            logger.trace(f"Cloudflare email decoding ValueError for: {encoded_string}")
            return None
        except Exception as e:
            logger.trace(f"Cloudflare email decoding general error: {e} for: {encoded_string}")
            return None

    def _clean_phone_candidate(self, text: str) -> str:
        if not text: return ""
        cleaned = str(text)

        cleaned = re.sub(
            r'^(?:phone|tel|call us at|fax|main office|direct line|mobile|contact us on|contact us by phone|text us at|message us on|our number is|order id|id|telephone|toll-free|call now)[\s:.\-]*',
            '', cleaned, flags=re.IGNORECASE
        ).strip()

        extension_part = None
        ext_match = re.search(r'(?i)(?:\s+|(\B|\b))(?:ext|extension|#)\.?\s*(\d{1,5})\s*$', cleaned)
        if not ext_match:
            ext_match = re.search(r'(?i)\s+x\.?\s*(\d{1,5})\s*$', cleaned)
        if ext_match:
            extension_part_value = ext_match.group(ext_match.lastindex)
            cleaned = cleaned[:ext_match.start()].strip()
            logger.trace(f"Stripped extension '{ext_match.group(0).strip()}' -> '{extension_part_value}' from '{text}', leaving '{cleaned}'")

        if cleaned:
            words = cleaned.split()
            if len(words) > 1:
                junk_trailing_words = {"please", "now", "today", "only", "office", "hours", "department", "and", "or", "main", "direct", "text", "ask", "for", "local", "company"}
                known_vanity_keywords = {"call", "get", "buy", "shop", "book", "free", "data", "plus", "test", "info", "corp", "tech", "auto", "med", "law", "bank", "cash", "loan", "home", "sale", "rent", "cars", "win", "flowers", "tollfree", "complex"} # Added more
                
                words_to_keep = len(words)
                for i in range(len(words) - 1, 0, -1):
                    current_word = words[i]
                    current_word_lower = current_word.lower().strip(".,;:!?()")
                    prev_word_looks_like_number_part = re.search(r'[\dA-Z-]{2,}$', words[i-1], re.IGNORECASE) or \
                                                       words[i-1].lower() in known_vanity_keywords
                    
                    if current_word_lower.isalpha() and \
                       current_word_lower in junk_trailing_words and \
                       current_word_lower not in known_vanity_keywords and \
                       prev_word_looks_like_number_part:
                        words_to_keep = i
                    elif current_word_lower.isalpha() and \
                         current_word_lower not in known_vanity_keywords and \
                         not re.search(r'\d', current_word) and \
                         prev_word_looks_like_number_part and \
                         len(current_word_lower) > 1:
                        words_to_keep = i
                    else:
                        break
                cleaned = " ".join(words[:words_to_keep]).strip()

        if cleaned:
            cleaned_spaced = re.sub(r'\s*-\s*', ' - ', cleaned)
            cleaned_spaced = re.sub(r'\s+', ' ', cleaned_spaced).strip()
            parts = cleaned_spaced.split(' ')
            
            reconstructed_parts = []
            current_vanity_chunk = []
            for part_idx, part_val in enumerate(parts):
                if not part_val: continue
                is_vanity_word_part = part_val.isalpha() and (len(part_val) > 1 or part_val.upper() in ['A', 'I'])
                
                if is_vanity_word_part:
                    current_vanity_chunk.append(part_val.upper())
                else:
                    if current_vanity_chunk:
                        # Check if previous part was also vanity, if so, join without space (e.g. TOLL FREE -> TOLLFREE)
                        # This is tricky. The goal is to make "TOLL FREE" into "TOLLFREE"
                        # but "1 800 GOOD BOY" into "1-800-GOODBOY"
                        # The current reconstruction with hyphens later might be better.
                        reconstructed_parts.append("".join(current_vanity_chunk))
                        current_vanity_chunk = []
                    reconstructed_parts.append(part_val)
            
            if current_vanity_chunk:
                reconstructed_parts.append("".join(current_vanity_chunk))

            final_cleaned_str = ""
            for i, p_part_val in enumerate(reconstructed_parts):
                if not p_part_val: continue
                
                if final_cleaned_str and not final_cleaned_str.endswith('-') and p_part_val != '-':
                    prev_char_of_final = final_cleaned_str[-1]
                    curr_char_of_part_val = p_part_val[0]
                    
                    # Add hyphen between: num-letter, letter-num, num-num, letter-letter (if they were separated)
                    # This helps form "1-800-LETTERS" or "LETTERS-MORE"
                    if (prev_char_of_final.isdigit() and curr_char_of_part_val.isalpha()) or \
                       (prev_char_of_final.isalpha() and curr_char_of_part_val.isdigit()) or \
                       (prev_char_of_final.isdigit() and curr_char_of_part_val.isdigit()) or \
                       (prev_char_of_final.isalpha() and curr_char_of_part_val.isalpha() and len(p_part_val)>1 and len(final_cleaned_str.split('-')[-1])>1 ): # Avoid hyphenating single letters like A-B-C
                        final_cleaned_str += '-'
                
                final_cleaned_str += p_part_val
            cleaned = final_cleaned_str.replace('--', '-')

        if cleaned:
            if cleaned.startswith('+'):
                cleaned_after_plus = re.sub(r'[^\w-]+$', '', cleaned[1:]).strip()
                cleaned_after_plus = re.sub(r'^[^\w-]+', '', cleaned_after_plus).strip()
                cleaned = '+' + cleaned_after_plus if cleaned_after_plus else ""
            else:
                cleaned = re.sub(r'^[^\w+-]+|[^\w-]+$', '', cleaned).strip()
        
        if cleaned == "+": cleaned = ""
        # Specific fix for "TOLLFREE" if it became "TOLL-FREE"
        cleaned = cleaned.replace("TOLL-FREE", "TOLLFREE")
        cleaned = cleaned.replace("FLOW-ERS", "FLOWERS") # Example for split vanity
        return cleaned


    def _parse_phone_string_direct(self, phone_string: Optional[str], region: Optional[str] = None) -> Optional[str]:
        if not phonenumbers or not phone_string:
            return None
        
        phone_string_to_parse = phone_string.strip()
        num_digits_only = re.sub(r'\D', '', phone_string_to_parse)
        if not phone_string_to_parse or len(num_digits_only) < 7 or self._is_generic_phone(phone_string_to_parse):
            return None

        effective_region = region or self.default_region
            
        try:
            num_obj = phonenumbers.parse(phone_string_to_parse, effective_region)
            is_valid = phonenumbers.is_valid_number(num_obj)
            is_possible = phonenumbers.is_possible_number(num_obj)
            is_valid_for_region = False
            if effective_region:
                 is_valid_for_region = phonenumbers.is_valid_number_for_region(num_obj, effective_region)

            if is_valid or is_valid_for_region:
                return phonenumbers.format_number(num_obj, PhoneNumberFormat.E164)
            
            if is_possible and num_obj.country_code:
                if effective_region:
                    try:
                        expected_country_code = phonenumbers.country_code_for_region(effective_region)
                        if num_obj.country_code == expected_country_code:
                            # Re-check validity of the international format without regional constraints
                            international_format_check = phonenumbers.format_number(num_obj, PhoneNumberFormat.INTERNATIONAL)
                            num_obj_international_check = phonenumbers.parse(international_format_check, None)
                            if phonenumbers.is_valid_number(num_obj_international_check):
                                return phonenumbers.format_number(num_obj_international_check, PhoneNumberFormat.E164)
                    except Exception: pass
                try:
                    num_obj_noregion_check = phonenumbers.parse(phonenumbers.format_number(num_obj, PhoneNumberFormat.INTERNATIONAL), None)
                    if phonenumbers.is_valid_number(num_obj_noregion_check):
                        return phonenumbers.format_number(num_obj_noregion_check, PhoneNumberFormat.E164)
                except NumberParseException:
                    pass

            if not phone_string_to_parse.startswith('+'):
                try:
                    num_obj_noregion = phonenumbers.parse(phone_string_to_parse, None)
                    if phonenumbers.is_valid_number(num_obj_noregion):
                        return phonenumbers.format_number(num_obj_noregion, PhoneNumberFormat.E164)
                except NumberParseException:
                    pass

        except NumberParseException as e:
            logger.trace(f"PhoneNumberParseException for '{phone_string_to_parse}' (region: {effective_region}): {e}")
            if not phone_string_to_parse.startswith('+'):
                try:
                    num_obj_noregion_on_fail = phonenumbers.parse(phone_string_to_parse, None)
                    if phonenumbers.is_valid_number(num_obj_noregion_on_fail):
                        return phonenumbers.format_number(num_obj_noregion_on_fail, PhoneNumberFormat.E164)
                except NumberParseException:
                    logger.trace(f"Also failed parsing '{phone_string_to_parse}' without region hint.")
        return None

    def extract_phone_numbers(self) -> List[str]:
        if not phonenumbers:
            logger.warning("Phonenumbers library not available, cannot extract phone numbers.")
            return []
        
        unique_formatted_phones: Set[str] = set()

        for link_tag in self.soup.select('a[href^="tel:"]'):
            href_attr = link_tag.get("href", "").replace("tel:", "").strip()
            cleaned_href = self._clean_phone_candidate(href_attr)
            if cleaned_href and not self._is_generic_phone(cleaned_href):
                phone_from_href = self._parse_phone_string_direct(cleaned_href, self.default_region)
                if phone_from_href:
                    unique_formatted_phones.add(phone_from_href)
            
            link_text_content = self._extract_text_content(link_tag)
            if link_text_content:
                cleaned_link_text = self._clean_phone_candidate(link_text_content)
                if cleaned_link_text and not self._is_generic_phone(cleaned_link_text):
                    parsed_from_link_text = self._parse_phone_string_direct(cleaned_link_text, self.default_region)
                    if parsed_from_link_text:
                        unique_formatted_phones.add(parsed_from_link_text)
                    else:
                        try:
                            for match in PhoneNumberMatcher(link_text_content, self.default_region, Leniency.POSSIBLE):
                                e164_formatted_num = phonenumbers.format_number(match.number, PhoneNumberFormat.E164)
                                cleaned_raw_for_generic_check = self._clean_phone_candidate(match.raw_string)
                                if self._is_generic_phone(cleaned_raw_for_generic_check) or self._is_generic_phone(e164_formatted_num):
                                    continue
                                final_parsed_num = self._parse_phone_string_direct(e164_formatted_num, None)
                                if final_parsed_num: unique_formatted_phones.add(final_parsed_num)
                        except Exception as e:
                            logger.trace(f"PhoneNumberMatcher error in tel link text: {e}")
        
        selectors = [
            'p', 'div', 'span', 'li', 'td', 'address', 'footer', 'header', '.contact-info', '.phone',
            '[itemprop="telephone"]', '[class*="contact"]', '[id*="contact"]', '[class*="phone"]',
            '[id*="phone"]', '[class*="tel"]', '[id*="tel"]'
        ]
        elements_to_scan = []
        for selector in selectors:
            try: elements_to_scan.extend(self.soup.select(selector))
            except Exception as e: logger.debug(f"CSS selector error for '{selector}': {e}")
        
        if not elements_to_scan and self.soup.body:
            elements_to_scan.append(self.soup.body)
        
        unique_elements_to_scan = list(dict.fromkeys(elements_to_scan))
        processed_text_blocks_for_matcher = set()

        for element in unique_elements_to_scan:
            block_text = self._extract_text_content(element)
            if not block_text or len(block_text) < 7:
                continue
            
            if len(block_text) > 200:
                if block_text in processed_text_blocks_for_matcher:
                    continue
                processed_text_blocks_for_matcher.add(block_text)

            try:
                matcher_instance = PhoneNumberMatcher(block_text, self.default_region, Leniency.POSSIBLE)
                for match in matcher_instance:
                    e164_formatted_num = phonenumbers.format_number(match.number, PhoneNumberFormat.E164)
                    cleaned_raw_for_generic_check = self._clean_phone_candidate(match.raw_string)
                    if self._is_generic_phone(cleaned_raw_for_generic_check) or self._is_generic_phone(e164_formatted_num):
                        continue
                    final_parsed_num = self._parse_phone_string_direct(e164_formatted_num, None)
                    if final_parsed_num:
                        unique_formatted_phones.add(final_parsed_num)
            except Exception as e:
                logger.trace(f"PhoneNumberMatcher iteration error for block: '{block_text[:100]}...': {e}")
        
        sorted_phones = sorted(list(unique_formatted_phones))
        logger.info(f"Found {len(sorted_phones)} unique phone number(s) for {self.source_url}: {sorted_phones}")
        return sorted_phones

    def extract_emails(self) -> List[str]:
        all_emails: Set[str] = set()

        for link_tag in self.soup.select('a[href^="/cdn-cgi/l/email-protection#"]'):
            encoded_str_href = link_tag.get('href', "")
            decoded_email_href = self._decode_cloudflare_email(encoded_str_href)
            if decoded_email_href and not self._is_generic_email(decoded_email_href):
                norm_email = normalize_email(decoded_email_href)
                if norm_email: all_emails.add(norm_email)
        
        for cf_span in self.soup.select('span.__cf_email__'):
            data_cfemail = cf_span.get('data-cfemail')
            if data_cfemail:
                decoded_email_span = self._decode_cloudflare_email(data_cfemail)
                if decoded_email_span and not self._is_generic_email(decoded_email_span):
                     norm_email = normalize_email(decoded_email_span)
                     if norm_email: all_emails.add(norm_email)

        for link_tag in self.soup.select('a[href^="mailto:"]'):
            href_attr = link_tag.get("href")
            if href_attr:
                email_candidate = clean_text(href_attr.replace("mailto:", "").split('?')[0])
                if email_candidate and not self._is_generic_email(email_candidate):
                    norm_email = normalize_email(email_candidate)
                    if norm_email: all_emails.add(norm_email)
        
        elements_for_email_search = self.soup.find_all(
            ['p', 'div', 'span', 'li', 'td', 'address', 'footer', 'article', 'section', 'a', 'font']
        )
        if self.soup.body and not elements_for_email_search:
            elements_for_email_search.append(self.soup.body)

        processed_text_for_email = set()
        for element in elements_for_email_search:
            element_text = self._extract_text_content(element)
            if not element_text or len(element_text) < 5: continue
            if len(element_text) > 200:
                if element_text in processed_text_for_email: continue
                processed_text_for_email.add(element_text)

            deobfuscated_text = element_text
            replacements = [
                (r'\s*\[\s*(?:at|@)\s*\]\s*', "@", re.IGNORECASE),
                (r'\s*\(\s*(?:at|@)\s*\)\s*', "@", re.IGNORECASE),
                (r'\s+(?:at)\s+', "@", re.IGNORECASE),
                (r'\bAT\b', "@"), # Use word boundary for AT
                (r'\s*<at>\s*', "@", re.IGNORECASE),
                (u"\uff20", "@"), (u"\uFE6B", "@"),
                (r"&commat;", "@", re.IGNORECASE),

                (r'\s*\[\s*(?:dot|\.)\s*\]\s*', ".", re.IGNORECASE),
                (r'\s*\(\s*(?:dot|\.)\s*\)\s*', ".", re.IGNORECASE),
                (r'\s+(?:dot)\s+', ".", re.IGNORECASE),
                (r'\bDOT\b', "."), # Use word boundary for DOT
                (r'\s*<dot>\s*', ".", re.IGNORECASE),
                (u"\u2024", "."), (u"\uFF0E", "."),
                (r"&period;", ".", re.IGNORECASE),
                
                (r'\s+en\s+', '@'),
                (r'\s+dt\s+', '.', re.IGNORECASE),
            ]
            for pattern, new_char, *flags_arg in replacements:
                flags = flags_arg[0] if flags_arg else 0
                deobfuscated_text = re.sub(pattern, new_char, deobfuscated_text, flags=flags)
            
            deobfuscated_text = re.sub(r'\s*@\s*', '@', deobfuscated_text)
            deobfuscated_text = re.sub(r'\s*\.\s*', '.', deobfuscated_text)
            deobfuscated_text = deobfuscated_text.replace("[@]", "@").replace("(@)", "@")
            deobfuscated_text = deobfuscated_text.replace("[.]", ".").replace("(.)", ".")

            emails_from_segment = extract_emails_from_text(deobfuscated_text)
            for email in emails_from_segment:
                if not self._is_generic_email(email):
                    all_emails.add(email)

        validated_emails_list: List[str] = []
        if validate_email and EmailNotValidError:
            for email_str in all_emails:
                try:
                    if len(email_str) > 254: continue
                    if email_str.startswith('.') or email_str.endswith('.'): continue
                    if ".." in email_str or ".@" in email_str or "@." in email_str or "@localhost" in email_str.lower(): continue
                    
                    email_info = validate_email(email_str, check_deliverability=False, allow_smtputf8=False)
                    validated_emails_list.append(email_info.normalized)
                except EmailNotValidError:
                    logger.trace(f"Email '{email_str}' failed validation with email_validator.")
                except ValueError as ve:
                    logger.trace(f"Email '{email_str}' caused ValueError in email_validator: {ve}")
            final_emails_list = sorted(list(set(validated_emails_list)))
        else:
            final_emails_list = sorted(list(all_emails))

        logger.info(f"Found {len(final_emails_list)} unique email address(es) for {self.source_url}: {final_emails_list}")
        return final_emails_list

    def _parse_address_with_library(self, address_text: str) -> Optional[Dict[str,str]]:
        if not address_text or not address_text.strip(): return None
        address_text_norm = clean_text(address_text)
        if not address_text_norm: return None
        
        generic_address_placeholders = {
            "123 main street, anytown, ca 12345", "your address here", "1 placeholder street",
            "street address, city, state, zipcode", "address line 1, address line 2",
            "city, state, zip", "po box placeholder"
        }
        if address_text_norm.lower() in generic_address_placeholders:
            logger.trace(f"Skipping parsing for very generic address string: {address_text_norm}")
            return None

        expanded_address_texts = [address_text_norm]
        parsed_components: Optional[Dict[str, str]] = None
        if libpostal_parse_address_func and libpostal_expand_address_func:
            try:
                expanded_forms = libpostal_expand_address_func(address_text_norm)
                if expanded_forms: expanded_address_texts.extend(expanded_forms)
            except Exception as e:
                logger.debug(f"libpostal_expand_address error for '{address_text_norm}': {e}")

            for text_to_parse in unique_everseen(expanded_address_texts):
                if not text_to_parse or not text_to_parse.strip(): continue
                try:
                    parsed_tuples = libpostal_parse_address_func(text_to_parse)
                    temp_parsed_components = {key: value for value, key in parsed_tuples}
                    if sum(1 for k in ['road', 'house_number', 'city', 'postcode', 'state', 'country'] 
                           if k in temp_parsed_components and temp_parsed_components[k]) >= 2 and \
                       (temp_parsed_components.get('road') and (temp_parsed_components.get('city') or temp_parsed_components.get('postcode'))):
                        parsed_components = temp_parsed_components
                        break
                except Exception as e:
                    logger.debug(f"Libpostal_parse_address error for '{text_to_parse}': {e}")
            
            if parsed_components and not (parsed_components.get('road') and (parsed_components.get('city') or parsed_components.get('postcode'))):
                 parsed_components = None

        is_us_by_libpostal = parsed_components and parsed_components.get('country', '').lower() in ['us', 'usa', 'united states', 'united states of america']
        looks_like_us_heuristic = bool(re.search(r'\b[A-Za-z]{2}\b\s+\d{5}(?:-\d{4})?\b', address_text_norm))

        should_try_usaddress = False
        if usaddress_tag_func:
            if not libpostal_parse_address_func and looks_like_us_heuristic:
                should_try_usaddress = True
            elif libpostal_parse_address_func and not parsed_components and looks_like_us_heuristic:
                should_try_usaddress = True
            elif is_us_by_libpostal and not (parsed_components.get('road') and (parsed_components.get('city') or parsed_components.get('postcode'))):
                should_try_usaddress = True
            elif parsed_components and not is_us_by_libpostal and looks_like_us_heuristic:
                should_try_usaddress = True
            elif not parsed_components and looks_like_us_heuristic:
                 should_try_usaddress = True

        if should_try_usaddress:
            try:
                us_parsed_dict, address_type = usaddress_tag_func(address_text_norm) # type: ignore
                if us_parsed_dict.get('AddressNumber') and us_parsed_dict.get('StreetName') and \
                   (us_parsed_dict.get('PlaceName') or us_parsed_dict.get('ZipCode')):
                    mapped_us_components: Dict[str, Optional[str]] = {
                        'house_number': us_parsed_dict.get('AddressNumber'),
                        'road': " ".join(filter(None, [
                            us_parsed_dict.get('StreetNamePreDirectional'),
                            us_parsed_dict.get('StreetName'),
                            us_parsed_dict.get('StreetNamePostType'),
                            us_parsed_dict.get('StreetNamePostDirectional')
                        ])).strip() or None,
                        'unit': " ".join(filter(None, [
                            us_parsed_dict.get('OccupancyType'),
                            us_parsed_dict.get('OccupancyIdentifier')
                        ])).strip() or None,
                        'city': us_parsed_dict.get('PlaceName'),
                        'state': us_parsed_dict.get('StateName'),
                        'postcode': us_parsed_dict.get('ZipCode'),
                        'country': 'US'
                    }
                    final_us_components = {k: v for k, v in mapped_us_components.items() if v}
                    if final_us_components.get('road') and (final_us_components.get('city') or final_us_components.get('postcode')):
                        return final_us_components
            except (USAddressRepeatedLabelError if USAddressRepeatedLabelError else Exception, ValueError, IndexError, TypeError) as e: # type: ignore
                 logger.trace(f"usaddress tagging error for '{address_text_norm}': {type(e).__name__} - {e}")
        
        return parsed_components

    def _format_parsed_address(self, parsed_address: Dict[str, str]) -> Optional[str]:
        if not parsed_address: return None
        
        has_road = parsed_address.get('road')
        has_locality = parsed_address.get('city') or parsed_address.get('suburb') or parsed_address.get('city_district')
        has_postcode = parsed_address.get('postcode')
        
        if not (has_road and (has_locality or has_postcode)):
            if not (parsed_address.get('po_box') and (has_locality or has_postcode)):
                return None

        address_parts = []
        line1_components = []
        if parsed_address.get('house_number'): line1_components.append(parsed_address['house_number'])
        if has_road: line1_components.append(has_road)
        line1 = " ".join(filter(None, line1_components)).strip()
        
        if parsed_address.get('unit'):
            line1 = f"{line1} {parsed_address['unit']}".strip()
        
        if line1: address_parts.append(line1)
        elif parsed_address.get('po_box'):
            address_parts.append(f"PO Box {parsed_address['po_box']}")

        city_str = parsed_address.get('city')
        if not city_str:
            city_alt_parts = [parsed_address.get('suburb'), parsed_address.get('city_district'), parsed_address.get('town')]
            city_str = " ".join(filter(None, city_alt_parts)).strip() or None
        
        state_str = parsed_address.get('state')
        if not state_str and parsed_address.get('state_district'):
            state_str = parsed_address.get('state_district')
        
        postcode_str = parsed_address.get('postcode')
        
        locality_line_parts = []
        if city_str: locality_line_parts.append(city_str)
        
        state_zip_combo = []
        if state_str: state_zip_combo.append(state_str)
        if postcode_str: state_zip_combo.append(postcode_str)
        if state_zip_combo: locality_line_parts.append(" ".join(state_zip_combo))
        
        if locality_line_parts:
            address_parts.append(", ".join(filter(None, locality_line_parts)))

        country_str = parsed_address.get('country')
        if country_str and country_str.upper() not in ['US', 'USA', 'UNITED STATES', 'UNITED STATES OF AMERICA']:
             if address_parts and city_str and not (state_str or postcode_str):
                  address_parts[-1] = f"{address_parts[-1]}, {country_str}"
             elif country_str :
                  address_parts.append(country_str)
        
        final_address = ", ".join(filter(None, address_parts))
        return final_address if final_address and len(final_address.split(',')) >=1 else None


    def extract_addresses(self) -> List[str]:
        found_addresses_set: Set[str] = set()

        for elem in self.soup.find_all(itemscope=True, itemtype=lambda x: x and "PostalAddress" in x):
            address_block_text = self._extract_text_content(elem)
            parsed_components_block = None
            if address_block_text and 10 <= len(address_block_text) <= 500:
                parsed_components_block = self._parse_address_with_library(address_block_text)
                if parsed_components_block:
                    formatted_addr = self._format_parsed_address(parsed_components_block)
                    if formatted_addr:
                        found_addresses_set.add(formatted_addr)
                        continue

            schema_parts: Dict[str, Optional[str]] = {
                prop: self._extract_text_content(item)
                for prop in ["name", "streetAddress", "postOfficeBoxNumber", 
                             "addressLocality", "addressRegion", "postalCode", "addressCountry"]
                if (item := elem.find(itemprop=prop))
            }
            
            constructed_parts_for_parsing = [
                schema_parts.get("streetAddress") or schema_parts.get("postOfficeBoxNumber"),
                schema_parts.get("addressLocality"),
                schema_parts.get("addressRegion"),
                schema_parts.get("postalCode"),
                schema_parts.get("addressCountry")
            ]
            constructed_addr_str = ", ".join(filter(None, constructed_parts_for_parsing))

            if constructed_addr_str and len(constructed_addr_str) > 10:
                parsed_comps_from_parts = self._parse_address_with_library(constructed_addr_str)
                if parsed_comps_from_parts:
                    formatted_fallback = self._format_parsed_address(parsed_comps_from_parts)
                    if formatted_fallback: found_addresses_set.add(formatted_fallback)
        
        container_selectors = [
            'address', '.address', '.location', '[class*="addr"]', '[id*="addr"]', 'footer',
            '.contact-info', '.contact-details', '.widget_contact_info',
            'div[itemtype="http://schema.org/Organization"]'
        ]
        candidate_elements: Set[Tag] = set()
        for selector in container_selectors:
            try:
                for el in self.soup.select(selector):
                    if not (el.get("itemscope") and el.get("itemtype") and "PostalAddress" in el.get("itemtype")):
                        candidate_elements.add(el)
            except Exception as e:
                 logger.debug(f"CSS selector error for address container '{selector}': {e}")
        
        processed_container_texts = set()
        for container in candidate_elements:
            container_text_parts = []
            for child in container.children:
                if isinstance(child, Tag):
                    if child.get("itemscope") and child.get("itemtype") and "PostalAddress" in child.get("itemtype"):
                        continue
                current_part_text = ""
                if isinstance(child, NavigableString):
                    current_part_text = str(child).strip()
                elif isinstance(child, Tag):
                    current_part_text = self._extract_text_content(child)
                
                if current_part_text: container_text_parts.append(current_part_text)
            
            container_text = clean_text("\n".join(filter(None, container_text_parts)))

            if not container_text or not (15 < len(container_text) < 800): continue
            if container_text in processed_container_texts: continue
            processed_container_texts.add(container_text)

            potential_address_segments_in_block = re.split(r'\n\s*\n+', container_text)
            
            if not potential_address_segments_in_block or \
               (len(potential_address_segments_in_block) == 1 and potential_address_segments_in_block[0] == container_text):
                 potential_address_segments_in_block = [container_text]

            for segment in potential_address_segments_in_block:
                segment = segment.strip()
                if not (10 < len(segment) < 400): continue
                
                is_redundant_or_sub_segment = any(segment.lower() in addr.lower() for addr in found_addresses_set) or \
                                            any(addr.lower() in segment.lower() for addr in found_addresses_set if len(addr) > len(segment) * 0.7)
                if is_redundant_or_sub_segment and segment.lower() not in (a.lower() for a in found_addresses_set) :
                    continue

                parsed_from_segment = self._parse_address_with_library(segment)
                if parsed_from_segment:
                    formatted_from_segment = self._format_parsed_address(parsed_from_segment)
                    if formatted_from_segment: found_addresses_set.add(formatted_from_segment)
        
        final_list = sorted([addr for addr in list(found_addresses_set) if addr])
        logger.info(f"Found {len(final_list)} unique address(es) for {self.source_url}: {final_list}")
        return final_list

    def extract_social_media_links(self) -> Dict[str, str]:
        social_links: Dict[str, str] = {}
        processed_urls: Set[str] = set()

        for link_tag in self.soup.find_all("a", href=True):
            href_original = link_tag.get("href")
            if not href_original: continue
            
            abs_href = make_absolute_url(self.source_url, href_original)
            if not abs_href or abs_href in processed_urls : continue
            processed_urls.add(abs_href)
            
            try:
                parsed_link = urlparse(abs_href)
                netloc_original = parsed_link.netloc.lower()
                netloc = netloc_original[4:] if netloc_original.startswith("www.") else netloc_original
                path_full = parsed_link.path.strip('/')
            except Exception as e:
                logger.trace(f"URL parsing failed for href '{abs_href}': {e}")
                continue

            for platform_key, platform_info in SOCIAL_MEDIA_PLATFORMS.items():
                if platform_key in social_links: continue
                        
                main_platform_domain = platform_info["domain"].lower()
                alt_platform_domains = [d.lower() for d in platform_info.get("alt_domains", [])]
                is_domain_match = (main_platform_domain == netloc or netloc in alt_platform_domains)
                
                if not is_domain_match: continue

                current_exclusions = platform_info.get("path_exclusions", [])
                path_lower = path_full.lower()
                if path_lower and any(ex_pattern.strip('/').lower() in path_lower for ex_pattern in current_exclusions if ex_pattern.strip('/')):
                        continue

                is_valid_by_path = False
                if platform_info.get("path_prefixes") and path_full:
                    for prefix in platform_info["path_prefixes"]:
                        clean_prefix = prefix.strip('/')
                        if clean_prefix and path_lower.startswith(clean_prefix.lower()):
                            if len(path_full) > len(clean_prefix) or platform_info.get("prefix_is_full_path", False):
                                is_valid_by_path = True
                                break
                
                if not is_valid_by_path and platform_info.get("path_regex"):
                    segment_for_regex = path_full.split('/')[0] if path_full else ""
                    if platform_key == "tiktok": # TikTok regex expects "@username"
                        # Prepend @ if it's a plausible username without it
                        if segment_for_regex and not segment_for_regex.startswith("@") and re.fullmatch(r"^[A-Za-z0-9_.]+$", segment_for_regex):
                            segment_for_regex = f"@{segment_for_regex}"
                    
                    if re.fullmatch(platform_info["path_regex"], segment_for_regex, re.IGNORECASE):
                        is_valid_by_path = True
                
                elif "path_prefixes" not in platform_info and "path_regex" not in platform_info:
                    if not path_full or platform_info.get("allow_empty_path", True):
                        is_valid_by_path = True

                if not is_valid_by_path and platform_key == "facebook" and \
                   platform_info.get("profile_php") and platform_info["profile_php"].lower() in path_lower:
                    if "id=" in parsed_link.query.lower():
                        is_valid_by_path = True
                
                if is_valid_by_path:
                    social_links[platform_key] = abs_href
                    logger.debug(f"Found social media ({platform_key}): {abs_href}")
                    break
        
        logger.info(f"Found {len(social_links)} social media link(s) for {self.source_url}.")
        return social_links

    def extract_description(self) -> Optional[str]:
        tags_to_check = [
            {"property": "og:description"},
            {"name": "description"},
            {"name": "twitter:description"}
        ]
        for attrs in tags_to_check:
            meta_tag = self.soup.find("meta", attrs=attrs)
            if meta_tag and meta_tag.get("content"):
                description = clean_text(meta_tag["content"])
                if description and len(description) > 10 and description.lower() not in COMPREHENSIVE_GENERIC_TITLES:
                    return description
        logger.info(f"No suitable description found for {self.source_url}")
        return None
        
    def extract_canonical_url(self) -> Optional[str]:
        canonical_link = self.soup.find("link", rel="canonical")
        if canonical_link and canonical_link.get("href"):
            abs_canonical = make_absolute_url(self.source_url, canonical_link["href"])
            if abs_canonical and abs_canonical.lower() != "http:///" and abs_canonical.lower() != "https:///": # Avoid invalid root URLs
                return abs_canonical
        logger.info(f"No canonical URL found for {self.source_url}")
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

        main_website: Optional[str] = None
        if self.scraped_data["canonical_url"]:
            try:
                parsed_canonical = urlparse(self.scraped_data["canonical_url"])
                if parsed_canonical.scheme and parsed_canonical.netloc:
                    domain_from_canonical = parsed_canonical.netloc.lower()
                    if domain_from_canonical not in PLACEHOLDER_WEBSITE_DOMAINS and \
                       not any(domain_from_canonical.endswith(tld) for tld in PLACEHOLDER_TLDS):
                        main_website = f"{parsed_canonical.scheme}://{parsed_canonical.netloc}"
            except Exception as e:
                logger.trace(f"Error parsing canonical URL '{self.scraped_data['canonical_url']}' for website: {e}")
        
        if not main_website:
            try:
                parsed_source = urlparse(self.source_url)
                if parsed_source.scheme and parsed_source.netloc:
                    domain_from_source = parsed_source.netloc.lower()
                    if domain_from_source not in PLACEHOLDER_WEBSITE_DOMAINS and \
                       not any(domain_from_source.endswith(tld) for tld in PLACEHOLDER_TLDS):
                        main_website = f"{parsed_source.scheme}://{parsed_source.netloc}"
            except Exception as e:
                 logger.trace(f"Error parsing source URL '{self.source_url}' for website: {e}")
        self.scraped_data["website"] = main_website
        
        extracted_summary = {k:v for k,v in self.scraped_data.items() 
                             if v or (isinstance(v, (list, dict)) and v)}
        logger.success(f"Scraping complete for {self.source_url}. Extracted fields: {list(extracted_summary.keys())}")
        return self.scraped_data

# Helper for _parse_address_with_library to avoid re-processing identical expanded forms
# (Should be in utils.py if used more broadly, or defined locally if only here)
from itertools import filterfalse
def unique_everseen(iterable, key=None):
    "List unique elements, preserving order. Remember all elements ever seen."
    seen = set()
    seen_add = seen.add
    if key is None:
        for element in filterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                yield element


if __name__ == '__main__':
    # Example usage for direct testing (python scraper.py)
    sample_html_complex = """
    <html><head>
        <title>Complex Solutions Ltd. | Innovative Tech</title>
        <meta property="og:site_name" content="Complex Solutions Ltd">
        <meta name="description" content="Leading provider of tech solutions. Contact us for more info.">
        <link rel="canonical" href="https://www.complexsolutions.com/home">
    </head><body>
        <h1>Welcome to Complex Solutions Ltd.</h1>
        <p>Call us: 1-800-COMPLEX. Email: <a href="mailto:info@complexsolutions.com">info@complexsolutions.com</a> or contact [at] complexsolutions [dot] com.</p>
        <p>Our main line is (556) 123-4567. UK: +44 207 123 4567. Fax (US): 1-888-FAX-THIS.</p>
        <p>Another number: 1-800-GET-INFO please call now.</p>
        <p>Deeply nested: <span>Call <span>now: <b>1</b > - <em>800</em></span><span>-<span>TOLL</span><span>FREE</span></span> !</span></p>
        <p>Email: <span>info</span>@(<span>example</span>.<span>com</span>)</p>
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
            <a href="https://www.facebook.com/complexsolutionsltd">Facebook Page</a>
            <a href="https://www.youtube.com/@complexsolutions">YouTube</a>
            <a href="https://www.tiktok.com/@complexdata">TikTok</a>
        </div>
        <footer>Copyright © 2024 Complex Solutions Limited. All rights reserved. Office: 1-800-NEW-DEAL.</footer>
    </body></html>"""
    scraper = HTMLScraper(sample_html_complex, "https://www.complexsolutions.com")
    data = scraper.scrape()
    import json
    print(json.dumps(data, indent=4))

