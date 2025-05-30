# lead_gen_pipeline/placeholder_data.py
# This file contains dictionaries and sets of placeholder values, generic terms,
# and patterns to be excluded during scraping to improve data quality.

# --- Generic Phone Number Patterns/Placeholders ---
# Stored as a set for efficient lookup.
# Note: Some patterns are better handled with regex, e.g., 555-01xx.
# The 555-0100 through 555-0199 range is specifically reserved for fictional use.
# Google recommends using US numbers in the range 800‑555‑0100 through 800‑555‑0199 for examples.
GENERIC_PHONE_PATTERNS = {
    # North American Placeholders
    "555-0100", "555-0101", "555-0199", # Common 555-01xx range
    "123-456-7890", "(123) 456-7890", "123.456.7890",
    "000-000-0000", "111-111-1111", "999-999-9999", "888-888-8888",
    "555-555-5555", "(555) 555-5555", "555.555.5555", # Generic 555
    "012-345-6789",
    "800-555-0100", "800-555-0150", "800-555-0199", # Google recommended range
    # Test/Novelty Numbers (US)
    "800-444-4444", # MCI/Verizon Caller ID Verification
    "804-222-1111", # Test calling service
    "909-390-0003", # Echo line
    # International Placeholders (Examples, more in research report)
    # Australia
    "(02) 5550 1234", "0491 570 123", "1800 160 401",
    # France
    "+33 1 99 00 00 00", "+33 6 39 98 00 00",
    # Germany
    "(030) 23125000", "(0171) 3920000",
    # UK
    "(0191) 498 0123", "020 7946 0123", "07700 900123", "0808 157 0123",
}

# --- Generic Email Addresses/Patterns ---
# Stored as a set for efficient lookup.
GENERIC_EMAIL_PATTERNS = {
    "email@example.com", "user@example.com", "info@example.com", "test@example.com",
    "admin@example.com", "contact@example.com", "yourname@example.com",
    "name@example.com", "[email protected]", "[email protected]",
    "example123@example.com", "testuser@example.com",
    "sales@example.com", "support@example.com", "noreply@example.com", "no-reply@example.com",
    "hello@example.com",
    "yourname@email.com", "name@domain.com", "email@domain.com",
    "info@domain.com", "sales@domain.com", "support@domain.com", "admin@domain.com",
    "contact@domain.com", "hello@domain.com",
    "info@mydomain.com", "contact@yourdomain.com",
    "[email protected]", "[email protected]", # GitHub specific
    "xxx@xxx.test",
    "84a6c63a-5634-45bf-b4a6-9c85443d@example.com", # GUID-based example
}
# Domains often used for placeholders
# IANA reserved: example.com, example.net, example.org, example.edu
# IANA reserved TLDs:.test,.example
GENERIC_EMAIL_DOMAINS = {
    "example.com", "example.net", "example.org", "example.edu",
    "domain.com", "mydomain.com", "yourdomain.com",
    "your-company.com", "site.com", "website.com",
    "email.com", # Often part of placeholder like yourname@email.com
    "company.com", # Generic
    "test.com", "demo.com", "anydomain.com",
    # TLDs (handle by checking domain ending, these are domains not TLDs themselves here)
    "xxx.test", # For emails like xxx@xxx.test
}

# --- Generic Company Name Parts & Titles ---
# Stored as a set for efficient lookup.
GENERIC_COMPANY_TERMS = {
    # Legal Suffixes (very common, often mandatory)
    "company", "co", "corporation", "corp", "incorporated", "inc", "limited", "ltd",
    "llc", "l.l.c.", "lp", "llp", "plc", "gmbh", "ag", "sarl", "pty ltd", "s.a.",
    "p.c.", "p.a.", "chartered",
    # Common Generic Descriptors/Types
    "solutions", "services", "group", "enterprises", "associates", "agency",
    "consulting", "consultants", "advisory", "technologies", "tech", "systems",
    "industries", "international", "global", "national", "local", "regional",
    "online", "web", "digital", "media", "marketing", "design", "network", "data",
    "software", "hardware", "innovations", "innovative", "ventures", "holdings",
    "partners", "labs", "laboratories", "studios", "bio", "pharma", "biotech",
    "health", "healthcare", "care", "financial", "finance", "capital", "management",
    "real estate", "construction", "logistics", "travel", "foods", "drinks",
    "apparel", "fashion", "auto", "automotive", "home", "trading", "manufacturing",
    "development", "products", "worldwide", "unlimited", "experts", "strategy", "strategies",
    "store", "shop", "boutique", "gallery", "center", "institute",
    "foundation", "organization", "association", "council", "bureau",
    "university", "college", "school", "academy",
    # Placeholder Phrases in Names/Titles
    "example", "template", "placeholder", "test", "demo", "sample",
    "your company name", "company name here", "site name", "site name here",
    "untitled document", "new page", "[your brand]", "my business", "website title",
    "lorem ipsum", "lorem ipsum dolor sit amet",
    "business name", "page title", "headline here", "your logo",
    # Common Page Titles / Navigation Labels (often indicate non-primary pages)
    "home", "homepage", "official site", "official website", "welcome to", "home page",
    "about us", "about", "about page", "our story", "our company", "who we are", "meet the team", "team", "history", "mission", "vision", "values", "culture",
    "contact us", "contact", "contact page", "support", "help", "faq", "locations", "branches",
    "services", "products", "features", "solutions", "platform",
    "login", "signin", "sign in", "logout", "sign out", "my account", "your account", "profile", "dashboard", "register", "signup", "sign up", "create account",
    "search", "search results", "results",
    "privacy policy", "privacy", "terms of service", "terms & conditions", "terms of use", "legal", "disclaimer", "accessibility",
    "blog", "news", "articles", "updates", "press", "media",
    "careers", "jobs", "work with us",
    "sitemap",
    "portfolio", "projects", "case studies", "gallery", "clients",
    "testimonials", "reviews",
    "shop", "store", # Already in descriptors, but also page titles
    "cart", "shopping cart", "basket", "checkout",
    "pricing", "plans",
    "events",
    "resources", "downloads", "whitepapers", "documentation",
    "investors",
    "forum", "community",
    "status", "api", "developers", "changelog", "roadmap",
    "get started", "learn more", "read more", "find out more", "view all", "shop now", "donate", "subscribe", "request a demo", "book now",
    "page not found", "404 error", "access denied", "forbidden",
    "under construction", "coming soon", "maintenance",
    "default page", "index", "welcome",
    "basic contact", "no info", # From previous test failures
}

# --- Generic Address Components ---
GENERIC_STREET_NUMBERS = {
    "123", "1", "0", "100", "999", "101", "1a",
    "po box 123", "ap #100", "unit 1",
}
GENERIC_STREET_NAMES = {
    "main street", "main st", "123 main street",
    "any street", "anystreet", "your street",
    "placeholder street", "sample road", "sample street", "test avenue", "test street", "demo street",
    "street name", "address line 1", "address line 2",
    "elm street", "high street", "acacia avenue",
    "1st street", "second street", "third avenue",
    "nulla st", "fusce rd", "ullamcorper street", "sit rd", "dictum av", "sodales av",
    "integer rd", "dolor av", "at rd", "tortor street", "nunc road", "viverra avenue",
    "curabitur rd", "iaculis st", "lacinia avenue", "sociosqu rd", "aliquet st",
    "diam rd", "fringilla avenue", "neque st", "non rd", "suspendisse av", "et rd",
    "arcu st", "tincidunt ave", "gravida st", "vel av", "in st", "pellentesque ave",
    "proin road", "risus st", "malesuada road", "ut ave", "eget st", "urna st",
    "duis rd", "lobortis ave", "feugiat st", "aenean avenue", "nascetur st",
}
GENERIC_CITY_NAMES = {
    "anytown", "any city", "your city", "placeholder city", "sample city",
    "test city", "demo city", "cityname", "townsville", "exampletown",
    "springfield", "podunk", "east cupcake", "timbuktu", "kalamazoo",
    "city", # literal
}
GENERIC_STATE_PROVINCE_CODES = {
    "xx", "yy", "zz", "aa", "ss", "99",
    "state", "province", "your state", "your province", "region", "anystate",
    "placeholder state", "placeholder province",
}
GENERIC_POSTAL_CODES = {
    "00000", "00000-0000", "99999", "99999-9999",
    "xxxxx", "abcde", "a1b 2c3", "#####",
    "12345", "12345-6789",
    "zipcode", "postalcode", "zip", "postal code", # Literal values
}
GENERIC_COUNTRY_NAMES = {
    "your country", "country name", "placeholder country", "country placeholder",
    "country", # Literal value
    "testland", "sampleland", "ruritania", "landia", "nowhereland",
}

# --- Generic Social Media Path Segments (for exclusion) ---
GENERIC_SOCIAL_MEDIA_PATHS = {
    # Authentication & Account Management
    "login", "signin", "signout", "logout", "auth", "oauth", "register", "signup", "join",
    "account", "accounts/edit", "profile/edit", "settings", "preferences", "security",
    "password", "verification", "forgot_password", "reset_password",
    # Navigation & Interaction
    "search", "find", "explore", "discover", "feed", "home", "newsfeed", "timeline",
    "notifications", "messages", "inbox", "direct", "chat",
    # Content Interaction & Creation
    "share", "sharer.php", "intent/tweet", "intent/post", "status/", "post/", "posts/",
    "view/", "watch",
    "new", "create", "compose", "upload", "edit",
    # Informational & Support
    "help", "support", "contact", "contact-us", "faq", "about", "company", "info", "blog", "news",
    # Legal & Policy
    "privacy", "terms", "legal", "cookies", "policy", "tos", "dmca",
    # Categorization & Organization
    "topics", "hashtags", "tags", "/tag/", "categories", "groups", "communities", "pages", "events",
    "media",
    # Business & Developer
    "jobs", "careers", "hiring", "opportunities", "ads", "advertising", "business", "brand",
    "developer", "developers", "api", "apps", "mobile", "download", "widgets", "plugins", "embed",
    "admin", "moderation", "dashboard", "analytics", "insights", "stats", "billing", "payment", "subscriptions",
    # Miscellaneous
    "activity", "recent", "stories", "reels", "live", "saved", "bookmarks", "collections",
    "places", "locations", "private",
    # Platform-specific examples
    "i/flow", "i/redirect", # Twitter internal
    "user/status", # Generic twitter status path part
    "p/", # Often Instagram posts, not profiles
    "pin/", # Pinterest pins
    "results", # YouTube search results
    "feed/subscriptions", # YouTube
    "company/", # LinkedIn company pages (when not a specific company name)
    "pages/creation/", # Facebook
    "ads/manager/", # Facebook
    "source/", # Pinterest source links
}

# --- Placeholder Website Domains ---
PLACEHOLDER_WEBSITE_DOMAINS = {
    # IANA Reserved
    "example.com", "example.net", "example.org", "example.edu",
    # Common Generic/Template
    "placeholder.com", "yourwebsite.com", "yourdomain.com", "sitename.com",
    "brandname.com", "mycompany.com", "your-company-name.com", "newsite.com",
    "website.com", "mysite.com", "template.com", "websitetemplate.com",
    "companyname.com", "businessname.com", "themedomain.com",
    "test.com", "demo.com",
    # "Coming Soon" / Parked Indicators
    "comingsoon.com", "underconstruction.com",
    "cpanel.com", # Example of a parked domain alias
    # Note:.test,.example,.localhost,.invalid are TLDs and should be checked at the TLD level.
}

# --- Placeholder TLDs (Top-Level Domains) ---
PLACEHOLDER_TLDS = {
    ".test", ".example", ".localhost", ".invalid",
}
