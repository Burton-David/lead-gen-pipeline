"""Deterministic HTML scraping and business-data extraction.

:class:`HTMLScraper` pulls company name, phone numbers, emails, addresses, social links,
description, and canonical URL from a single page using metadata, schema.org markup,
``tel:``/``mailto:`` links, and text heuristics. Generic and placeholder values are
filtered out via :mod:`lead_gen_pipeline.generic_filters`.
"""

import re
import unicodedata
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup, NavigableString, Tag

try:
    from .generic_filters import (
        GENERIC_COMPANY_TERMS,
        GENERIC_EMAIL_DOMAINS,
        GENERIC_EMAIL_PATTERNS,
        GENERIC_PHONE_PATTERNS,
        PLACEHOLDER_TLDS,
        PLACEHOLDER_WEBSITE_DOMAINS,
    )
    from .utils import (
        clean_text,
        extract_emails_from_text,
        logger,
        make_absolute_url,
        normalize_email,
    )
except ImportError:
    from lead_gen_pipeline.generic_filters import (  # type: ignore
        GENERIC_COMPANY_TERMS,
        GENERIC_EMAIL_DOMAINS,
        GENERIC_EMAIL_PATTERNS,
        GENERIC_PHONE_PATTERNS,
        PLACEHOLDER_TLDS,
        PLACEHOLDER_WEBSITE_DOMAINS,
    )
    from lead_gen_pipeline.utils import (  # type: ignore
        clean_text,
        extract_emails_from_text,
        logger,
        make_absolute_url,
        normalize_email,
    )

# Optional dependencies
try:
    import phonenumbers
    from phonenumbers import NumberParseException, PhoneNumberFormat

    PHONENUMBERS_AVAILABLE = True
except ImportError:  # pragma: no cover - phonenumbers is a core dependency
    phonenumbers = None  # type: ignore[assignment]
    PhoneNumberFormat = None  # type: ignore[assignment,misc]
    NumberParseException = None  # type: ignore[assignment,misc]
    PHONENUMBERS_AVAILABLE = False
    logger.warning("phonenumbers library not available")

try:
    import spacy

    try:
        NLP_SPACY = spacy.load("en_core_web_sm")
    except OSError:
        NLP_SPACY = None
except ImportError:  # pragma: no cover - spaCy is an optional extra
    spacy = None  # type: ignore[assignment]
    NLP_SPACY = None

try:
    from email_validator import EmailNotValidError, validate_email

    EMAIL_VALIDATOR_AVAILABLE = True
except ImportError:  # pragma: no cover - email-validator is a core dependency
    validate_email = None  # type: ignore[assignment]
    EmailNotValidError = None  # type: ignore[assignment,misc]
    EMAIL_VALIDATOR_AVAILABLE = False

SOCIAL_MEDIA_PLATFORMS: dict[str, dict[str, Any]] = {
    "linkedin": {
        "domains": ["linkedin.com", "www.linkedin.com"],
        "valid_paths": ["/company/", "/in/", "/school/", "/pub/"],
        "exclude_paths": ["login", "signup", "help", "legal", "feed", "shareArticle"],
    },
    "twitter": {
        "domains": ["twitter.com", "www.twitter.com", "x.com", "www.x.com"],
        "username_pattern": r"^[A-Za-z0-9_]{1,15}$",
        "exclude_paths": [
            "search",
            "intent",
            "login",
            "home",
            "explore",
            "settings",
            "i/",
        ],
    },
    "facebook": {
        "domains": ["facebook.com", "www.facebook.com", "fb.com"],
        "valid_paths": ["/pages/", "/pg/"],
        "username_pattern": r"^[a-zA-Z0-9._-]+/?$",
        "exclude_paths": ["login", "sharer", "dialog", "help", "terms", "ads"],
    },
    "instagram": {
        "domains": ["instagram.com", "www.instagram.com"],
        "username_pattern": r"^[A-Za-z0-9_.\-]+/?$",
        "exclude_paths": ["/p/", "/reels/", "/explore/", "/accounts/", "login"],
    },
    "youtube": {
        "domains": ["youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"],
        "valid_paths": ["/channel/", "/c/", "/user/", "/@"],
        "username_pattern": r"^[A-Za-z0-9_.-]+$",
        "exclude_paths": [
            "/watch",
            "/embed",
            "/results",
            "/shorts",
            "login",
            "account",
        ],
    },
    "pinterest": {
        "domains": ["pinterest.com", "www.pinterest.com", "pinterest.co.uk"],
        "username_pattern": r"^[A-Za-z0-9_]+/?$",
        "exclude_paths": ["/pin/", "/search/", "login", "/settings/"],
    },
    "tiktok": {
        "domains": ["tiktok.com", "www.tiktok.com"],
        "username_pattern": r"^@[A-Za-z0-9_.]+$",
        "exclude_paths": ["/tag/", "/search", "login", "/upload"],
    },
}


class HTMLScraper:
    """Extracts structured business data from a single HTML page.

    Construct with the page HTML and its source URL, then call :meth:`scrape` for the
    full record, or the individual ``extract_*`` methods for one field at a time.
    """

    def __init__(self, html_content: str, source_url: str):
        if not html_content:
            logger.warning(f"Empty HTML content for URL: {source_url}")
            self.soup = BeautifulSoup("", "html.parser")
        else:
            self.soup = BeautifulSoup(html_content, "html.parser")
        self.source_url = source_url
        self.default_region = "US"

    @staticmethod
    def _attr(node: Any, name: str) -> str | None:
        """Return a tag attribute as a string, or None if absent or multi-valued."""
        if isinstance(node, Tag):
            value = node.get(name)
            if isinstance(value, str):
                return value
        return None

    def _is_generic_phone(self, phone_text: str) -> bool:
        """Check if phone number is placeholder/generic."""
        if not phone_text:
            return False

        normalized = re.sub(r"[^\da-zA-Z]", "", phone_text).lower()

        for pattern in GENERIC_PHONE_PATTERNS:
            pattern_normalized = re.sub(r"[^\da-zA-Z]", "", pattern).lower()
            if pattern_normalized == normalized:
                return True

        # Check for repeated digits
        digits_only = re.sub(r"\D", "", phone_text)
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

        if "@" in email_lower:
            domain = email_lower.rsplit("@", 1)[1]
            if domain in GENERIC_EMAIL_DOMAINS:
                return True
            if any(domain.endswith(tld) for tld in PLACEHOLDER_TLDS):
                return True

        return False

    def _extract_text_content(self, element: Tag | None) -> str | None:
        """Extract and clean text from element."""
        if not element:
            return None

        try:
            text = element.get_text(separator=" ", strip=True)
        except Exception as e:
            logger.debug(f"get_text failed; falling back to manual traversal: {e}")
            texts = []
            for item in element.descendants:
                if isinstance(item, NavigableString):
                    parent_name = getattr(item.parent, "name", "")
                    if parent_name not in ["script", "style", "noscript"]:
                        texts.append(str(item))
            text = " ".join(texts)

        if not text:
            return None

        # Unicode normalization
        text = unicodedata.normalize("NFKC", text)
        text = text.replace("\xa0", " ")

        # Normalize hyphens
        for char in "‑–—−‒―‐":
            text = text.replace(char, "-")

        cleaned = clean_text(text)
        return cleaned if cleaned else None

    def extract_company_name(self) -> str | None:
        """Extract company name from various page elements."""
        candidates = []

        # og:site_name meta tag
        og_site_name = self.soup.find("meta", property="og:site_name")
        site_name_content = self._attr(og_site_name, "content")
        if site_name_content:
            name = clean_text(site_name_content)
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
        og_title_content = self._attr(og_title, "content")
        if og_title_content:
            title_content = clean_text(og_title_content)
            if title_content and title_content.lower() not in GENERIC_COMPANY_TERMS:
                parts = re.split(r"\s*[\|\-–—]\s*", title_content)
                if len(parts) > 1:
                    company_part = clean_text(parts[-1])
                    if (
                        company_part
                        and company_part.lower() not in GENERIC_COMPANY_TERMS
                    ):
                        candidates.append((company_part, 8))
                else:
                    candidates.append((title_content, 6))

        # Page title
        title_tag = self.soup.title
        if title_tag:
            title_text = self._extract_text_content(title_tag)
            if title_text and title_text.lower() not in GENERIC_COMPANY_TERMS:
                parts = re.split(r"\s*[\|\-–—]\s*", title_text)
                if len(parts) > 1:
                    company_part = clean_text(parts[-1])
                    if (
                        company_part
                        and company_part.lower() not in GENERIC_COMPANY_TERMS
                    ):
                        candidates.append((company_part, 7))

        # Copyright footer
        footer = self.soup.find("footer")
        if footer:
            footer_text = self._extract_text_content(footer)
            if footer_text:
                copyright_match = re.search(
                    r"©\s*(?:\d{4}[-\s]?\d{4}|\d{4})?\s*([^.,\n]+?)"
                    r"(?:\s*(?:All Rights Reserved|Inc\.?|LLC|Ltd\.?|Corp\.?))?"
                    r"(?:\.|$)",
                    footer_text,
                    re.IGNORECASE,
                )
                if copyright_match:
                    company_name = clean_text(copyright_match.group(1))
                    if (
                        company_name
                        and company_name.lower() not in GENERIC_COMPANY_TERMS
                    ):
                        candidates.append((company_name, 6))

        # NLP extraction fallback
        if NLP_SPACY and not candidates:
            h1 = self.soup.find("h1")
            if h1:
                h1_text = self._extract_text_content(h1)
                if h1_text and len(h1_text) < 100:
                    try:
                        doc = NLP_SPACY(h1_text)
                        for ent in doc.ents:
                            if ent.label_ == "ORG":
                                org_name = clean_text(ent.text)
                                if (
                                    org_name
                                    and org_name.lower() not in GENERIC_COMPANY_TERMS
                                ):
                                    candidates.append((org_name, 4))
                    except Exception as e:
                        logger.debug(f"spaCy NER fallback failed for company name: {e}")

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _decode_cloudflare_email(self, encoded_string: str) -> str | None:
        """Decode Cloudflare email protection."""
        try:
            if encoded_string.startswith("/cdn-cgi/l/email-protection#"):
                encoded_string = encoded_string.split("#")[-1]

            if len(encoded_string) < 2:
                return None

            r = int(encoded_string[:2], 16)
            email = "".join(
                [
                    chr(int(encoded_string[i : i + 2], 16) ^ r)
                    for i in range(2, len(encoded_string), 2)
                ]
            )
            return email
        except (ValueError, IndexError):
            return None

    def _clean_phone_text(self, text: str) -> str:
        """Clean phone number text."""
        if not text:
            return ""

        text = re.sub(r"^(?:phone|tel|call|fax):?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(
            r"\s*(?:ext|x|extension)\.?\s*\d+\s*$", "", text, flags=re.IGNORECASE
        )
        text = re.sub(r"\s+", " ", text).strip()

        # Handle vanity numbers
        parts = text.split()
        cleaned_parts = []
        current_vanity = []

        for part in parts:
            if re.match(r"^[A-Z]+$", part) and len(part) > 1:
                current_vanity.append(part)
            else:
                if current_vanity:
                    cleaned_parts.append("".join(current_vanity))
                    current_vanity = []
                cleaned_parts.append(part)

        if current_vanity:
            cleaned_parts.append("".join(current_vanity))

        return " ".join(cleaned_parts)

    def _parse_phone_number(self, phone_text: str) -> str | None:
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

            if not phone_text.startswith("+"):
                number = phonenumbers.parse(phone_text, None)
                if phonenumbers.is_valid_number(number):
                    return phonenumbers.format_number(number, PhoneNumberFormat.E164)

        except NumberParseException:
            # Text that does not parse is simply not a phone number.
            return None

        return None

    def extract_phone_numbers(self) -> list[str]:
        """Extract phone numbers from HTML."""
        if not PHONENUMBERS_AVAILABLE:
            return []

        phones: set[str] = set()

        # Extract from tel: links
        for link in self.soup.find_all("a", href=True):
            href = self._attr(link, "href") or ""
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
            "p",
            "div",
            "span",
            "address",
            "footer",
            '[class*="contact"]',
            '[class*="phone"]',
            '[class*="tel"]',
        ]

        for selector in selectors:
            try:
                for element in self.soup.select(selector):
                    text = self._extract_text_content(element)
                    if not text:
                        continue

                    phone_patterns = [
                        r"\+?1?[-.\s]?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})",
                        r"\+?(\d{1,3})[-.\s]?(\d{3,4})[-.\s]?(\d{3,4})[-.\s]?(\d{3,4})",
                        r"\b1[-.\s]?800[-.\s]?[A-Z]{3}[-.\s]?[A-Z]{4}\b",
                    ]

                    for pattern in phone_patterns:
                        matches = re.finditer(pattern, text, re.IGNORECASE)
                        for match in matches:
                            parsed = self._parse_phone_number(match.group(0))
                            if parsed:
                                phones.add(parsed)
            except Exception as e:
                logger.debug(f"Phone extraction skipped selector '{selector}': {e}")
                continue

        return sorted(phones)

    def extract_emails(self) -> list[str]:
        """Extract email addresses from HTML."""
        emails: set[str] = set()

        # Cloudflare protection
        for link in self.soup.find_all("a", href=True):
            href = self._attr(link, "href") or ""
            if "email-protection" in href:
                decoded = self._decode_cloudflare_email(href)
                if decoded and not self._is_generic_email(decoded):
                    normalized = normalize_email(decoded)
                    if normalized:
                        emails.add(normalized)

        # mailto links
        for link in self.soup.find_all("a", href=True):
            href = self._attr(link, "href") or ""
            if href.startswith("mailto:"):
                raw = href.replace("mailto:", "").split("?")[0]
                email = clean_text(raw)
                if email and not self._is_generic_email(email):
                    normalized = normalize_email(email)
                    if normalized:
                        emails.add(normalized)

        # Text content with deobfuscation
        text_elements = self.soup.find_all(["p", "div", "span", "address", "footer"])
        for element in text_elements:
            text = self._extract_text_content(element)
            if not text:
                continue

            # Deobfuscate patterns
            text = re.sub(r"\s*\[at\]\s*", "@", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*\(at\)\s*", "@", text, flags=re.IGNORECASE)
            text = re.sub(r"\s+at\s+", "@", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*\[dot\]\s*", ".", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*\(dot\)\s*", ".", text, flags=re.IGNORECASE)
            text = re.sub(r"\s+dot\s+", ".", text, flags=re.IGNORECASE)

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

        return sorted(emails)

    def extract_addresses(self) -> list[str]:
        """Extract addresses from HTML."""
        addresses = set()

        # Schema.org markup
        for address_elem in self.soup.find_all(
            itemtype=lambda x: x and "PostalAddress" in x
        ):
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
                parts.append(
                    f"{self._extract_text_content(region)} "
                    f"{self._extract_text_content(postcode)}"
                )
            elif region:
                parts.append(self._extract_text_content(region))
            elif postcode:
                parts.append(self._extract_text_content(postcode))

            if len(parts) >= 2:
                address = ", ".join(filter(None, parts))
                if address:
                    addresses.add(address)

        # Common containers
        selectors = ["address", ".address", ".location", '[class*="addr"]', "footer"]

        for selector in selectors:
            try:
                for element in self.soup.select(selector):
                    text = self._extract_text_content(element)
                    if not text or len(text) < 10:
                        continue

                    # Basic address pattern matching
                    if re.search(r"\d+\s+\w+.*\b[A-Z]{2}\b\s+\d{5}", text):
                        addresses.add(text)
                    elif re.search(r"\d+.*\w+.*\d{5}", text):
                        addresses.add(text)
            except Exception as e:
                logger.debug(f"Address extraction skipped selector '{selector}': {e}")
                continue

        return sorted(addresses)

    def _is_valid_social_url(self, url: str, platform: str) -> bool:
        """Validate social media URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace("www.", "")
            path = parsed.path.strip("/")

            platform_config = SOCIAL_MEDIA_PLATFORMS.get(platform, {})

            if domain not in platform_config.get("domains", []):
                return False

            exclude_paths = platform_config.get("exclude_paths", [])
            for exclude in exclude_paths:
                if exclude in path.lower():
                    return False

            valid_paths = platform_config.get("valid_paths", [])
            if valid_paths:
                if not any(path.startswith(vp.strip("/")) for vp in valid_paths):
                    return False
            else:
                username_pattern = platform_config.get("username_pattern")
                if username_pattern:
                    username = path.split("/")[0] if path else ""
                    if platform == "tiktok" and not username.startswith("@"):
                        username = f"@{username}"
                    if not re.match(username_pattern, username):
                        return False

            return True

        except Exception as e:
            logger.debug(f"Social URL validation failed for '{url}' ({platform}): {e}")
            return False

    def extract_social_media_links(self) -> dict[str, str]:
        """Extract social media profile links."""
        social_links: dict[str, str] = {}

        for link in self.soup.find_all("a", href=True):
            href = self._attr(link, "href")
            if not href:
                continue

            abs_url = make_absolute_url(self.source_url, href)
            if not abs_url:
                continue

            for platform in SOCIAL_MEDIA_PLATFORMS:
                if platform in social_links:
                    continue

                if self._is_valid_social_url(abs_url, platform):
                    social_links[platform] = abs_url
                    break

        return social_links

    def extract_description(self) -> str | None:
        """Extract page description."""
        meta_specs: list[dict[str, Any]] = [
            {"property": "og:description"},
            {"name": "description"},
            {"name": "twitter:description"},
        ]

        for attrs in meta_specs:
            content = self._attr(self.soup.find("meta", attrs=attrs), "content")
            if content:
                desc = clean_text(content)
                if (
                    desc
                    and len(desc) > 10
                    and desc.lower() not in GENERIC_COMPANY_TERMS
                ):
                    return desc

        return None

    def extract_canonical_url(self) -> str | None:
        """Extract canonical URL."""
        href = self._attr(self.soup.find("link", rel="canonical"), "href")
        if href:
            return make_absolute_url(self.source_url, href)
        return None

    def scrape(self) -> dict[str, Any]:
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
            "scraped_from_url": self.source_url,
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
        except Exception as e:
            logger.debug(f"Could not derive website from {self.source_url}: {e}")
            data["website"] = None

        logger.success(f"Scraping complete: {self.source_url}")
        return data
