# Lead Generation Pipeline - Project Handoff
**Generated:** 2025-05-26 18:20:15 UTC

## Prompt for New Gemini Session (to accompany this document)
```text
Hello Gemini,

I'm working on a B2B lead generation pipeline project in Python. We've made significant progress on the foundational modules, and I need you to pick up where my previous session left off.

I'm providing this Markdown document that contains:
1.  The original project requirements and goals.
2.  The agreed-upon project directory structure.
3.  The complete code for all the Python files we've created and tested so far (`config.py`, `utils.py`, `crawler.py`, `scraper.py`, and their corresponding unit test files).
4.  The latest version of our "Developer Documentation" (`DEV_DOCUMENTATION.md`), which includes the current status of each module, coding conventions, testing strategy, and the future roadmap.
5.  A summary of our effective collaboration methods.

**Current Project Status (as per the Developer Documentation in this file - v0.1.7):**
* `config.py`: Complete and tested.
* `utils.py`: Complete and tested (includes logging, async retry, text/URL utilities, domain rate limiter).
* `crawler.py`: Complete and tested (HTTPX, Playwright, Robots.txt handling).
* `scraper.py`: Basic extraction methods for key data points (company name, phone, email, address, social links, description, canonical URL) are complete and tested.
* The Developer Documentation also outlines that the next steps involve `models.py` (defining data structures) and `database.py` (saving scraped data).

**Your Task:**
Please carefully review this entire Markdown document to understand the project's scope, the code developed so far, our coding standards, testing strategy, and our immediate next steps.

Once you've processed the document, please:
1.  Confirm you understand the current state and the next immediate task: designing and implementing `models.py` and `database.py`.
2.  Based on the data extracted by `scraper.py` (see its `scrape()` method return structure and the `DEV_DOCUMENTATION.md`), propose a SQLAlchemy model for a `Lead` in `models.py`. Consider how to store list-based data (e.g., phone numbers, emails) and dictionary-based data (social media links) in an SQLite database (e.g., using JSON strings or separate tables for MVP).
3.  Outline the basic functions needed in `database.py` (e.g., `init_db()` to create tables, `save_lead(lead_data: Dict[str, Any])` to store a lead).
4.  Provide the initial Python code for `models.py` and `database.py`, along with their corresponding test files (`tests/unit/test_models.py` and `tests/unit/test_database.py`).

**Collaboration Style:**
* Please provide complete, runnable code blocks (Canvases/Immersive Documents) for new or updated files.
* Include version comments (e.g., `# Version: Gemini-YYYY-MM-DD HH:MM UTC`) at the top of code files.
* We will work step-by-step. I will execute the code/tests you provide and share the exact terminal output for debugging.
* We will keep the Developer Documentation updated as we complete features.

Let's start with the design discussion for `models.py` and `database.py`.
```

## 1. Original Project Requirements & Goal
Your Persona: 
 You are a brilliant, experienced full-stack data scientist and software engineer building an advanced, production-ready lead generation pipeline. 

 You are designing this for a stealth B2B analytics tool that scrapes, enriches, and stores business leads from across thousands of diverse company and directory websites. 
 You’ve previously deployed real-world data systems that operate at scale without getting detected, flagged, blocked, or throttled. 
 You follow industry best practices, use elegant and reusable code, and understand the nuances of web crawling at scale — including stealth, concurrency, retries, distributed architecture, and post-processing. 
 Your job is to build this entire system end-to-end, as if it were to be used in production today. 
 🚀 Project Name: btl-lead-gen-pipeline 
 🎯 Goal: 
 Develop a Python-based data pipeline that: 

 Scrapes B2B lead data (company names, websites, emails, phone numbers, addresses, descriptions, industries) 
 Cleans and normalizes the data 
 Enriches leads using multiple strategies (e.g., LinkedIn, email pattern detection, domain analysis) 
 Stores results in a structured SQL database 
 Operates stealthily and ethically at scale using concurrency, proxy rotation, and CAPTCHA bypass tools 
 Is resilient, debuggable, and modular — easily extendable to new domains 
 🏗️ System Architecture Overview 
 Main Components: 

 urls.txt — A growing list of company or directory URLs to target 
 crawler.py — Site-specific logic to crawl and extract raw HTML 
 scraper.py — Parses and extracts structured lead information from HTML 
 enricher.py — Enhances raw leads (e.g., domain pattern matching for emails, LinkedIn lookups, etc.) 
 database.py — SQLAlchemy models for storing structured leads 
 config.py — All constants, user-agent strings, proxy lists, wait timings 
 utils.py — Shared utility functions (retry logic, HTML cleanup, etc.) 
 run_pipeline.py — Orchestration script that pulls it all together 
 Optional: 

 Dockerfile, docker-compose.yml for deployment 
 scheduler.py for cron-based jobs 
 Optional API layer via FastAPI to serve collected leads 
 logs/, errors/, .env.example for environmental variables 
 ⚙️ Functional Requirements 
 Crawling 
 Mimics real user behavior with rotating User-Agent, screen size, and IP 
 Uses headless browsers (e.g., undetected-chromedriver, Playwright) for JS-heavy sites 
 Handles redirects, retries, robots.txt, and soft throttling 
 Implements adaptive wait times and asyncio-based concurrency 
 Can rotate proxies (with optional 3rd party tools like BrightData, ScraperAPI) 
 Supports CAPTCHA bypass via 2Captcha or Selenium plugin tools 
 Logs errors and response times 
 Scraping 
 Modular design to plug in new site parsers (parse_directory_x, parse_company_y) 
 Extracts: 
 Company name 
 Website 
 Email(s) 
 Phone number(s) 
 LinkedIn / Twitter / Facebook URLs 
 HQ address 
 NAICS/SIC code if available 
 Industry tags 
 Applies post-processing: email regex normalization, fuzzy matching, deduplication 
 Enrichment 
 Email domain pattern prediction (e.g., first.last@domain) 
 Web archive or whois to verify domain age or owner 
 Reverse image search (optional) to detect company logos 
 LinkedIn automation for cross-matching companies to real profiles 
 Adds metadata like confidence score, source URL, scraped_at timestamp 
 Database Layer 
 SQLAlchemy-backed PostgreSQL or SQLite 
 Models: Lead, Company, Contact, Source 
 Deduplication logic (company + email as composite key) 
 Uses Alembic for migrations 
 Option to export to .csv, .json, or parquet 
 Concurrency & Scheduling 
 Uses asyncio and aiohttp or httpx with semaphore logic 
 Ensures no domain is hit concurrently 
 Adds rate_limit() and backoff() utilities 
 Built-in retry with exponential backoff and jitter 
 Optional: supports Celery-based distributed tasking or FastAPI endpoint for async job queue 
 Stealth Mode 
 Uses multiple layers of obfuscation: 
 Rotating User-Agent (desktop/mobile/browser mix) 
 Viewport spoofing 
 Referer spoofing 
 Headless + mouse movement simulation (e.g., pyppeteer_stealth) 
 Dynamic typing and scrolling on load 
 Randomizes delays between page requests 
 Maintains rolling error log per domain 
 🧪 Testing & Monitoring 
 Unit tests for every major module (pytest) 
 Try/except blocks around all external requests, with categorized error handling 
 Verbose logging using loguru or structlog 
 Logging to both terminal and rolling .log file 
 Test mode to run on mock HTML or subset of URLs 
 📦 Extra Credit (Highly Impressive Extras) 
 Integrate with Pinecone or FAISS for vector search over descriptions 
 Slack or Discord notification on scraping session success/failure 
 Optional FastAPI GUI to query the lead DB 
 Admin CLI (typer) to ingest new URLs, preview parsed leads, or reprocess errors 
 Docker container with rotating proxies baked in 
 🧑‍💼 Final Output & Deliverables 
 A complete GitHub repository with: 
 Working, tested code 
 Structured folder layout 
 Setup instructions 
 Simulated demo run (using 10 real business directory pages) 
 Markdown README with: Overview, Features, Architecture Diagram, Setup, Usage, Future Work 
 ✅ Reminders 
 Do not overload any domain. Respect practical ethical boundaries. 
 Mimic real users intelligently. 
 Show off your understanding of stealth scraping, pipeline engineering, and real-world data challenges.

## 2. Effective Collaboration Methods Summary
* Work step-by-step: AI provides code/instructions for one specific task, user executes and provides full terminal output for debugging.
* Terminal output is the source of truth for debugging.
* Code provided in complete, runnable blocks (Canvases/Immersive Documents).
* Version comments (e.g., `# Version: Gemini-YYYY-MM-DD HH:MM UTC`) at the top of Python files provided by the AI.
* Keep `DEV_DOCUMENTATION.md` updated with each completed feature.
* Focus on robust, well-tested, production-quality code.
* Prioritize ethical crawling, with advanced stealth as a later enhancement.
* User manages local files and Git repository. AI provides code and guidance.

## 3. Project Directory Tree
```
lead-gen-pipeline/
├── .env
├── .env.example
├── .gitignore
├── DEV_DOCUMENTATION.md
├── README.md
├── requirements.txt
├── cli_mvp.py
├── run_pipeline_mvp.py
│
├── data/
│   └── urls_seed.csv
│
├── lead_gen_pipeline/
│   ├── __init__.py
│   ├── config.py
│   ├── crawler.py
│   ├── database.py
│   ├── llm_handler.py
│   ├── models.py
│   ├── scraper.py
│   └── utils.py
│
├── logs/
│   └── app.log
│
├── reports/
│   ├── crawl_reports/
│   └── test_reports/
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    │
    ├── integration/
    │   ├── __init__.py
    │   └── test_pipeline_flow.py
    │
    └── unit/
        ├── __init__.py
        ├── test_config.py
        ├── test_crawler.py
        ├── test_database.py
        ├── test_llm_handler.py
        ├── test_models.py
        ├── test_scraper.py
        └── test_utils.py
```

## 4. Developer Documentation (`DEV_DOCUMENTATION.md`)

---

B2B Lead Generation Pipeline - Developer Documentation
Version: 0.1.7 (MVP - Scraper Basic Extraction Methods Complete)
Last Updated: 2025-05-26 14:05 EDT

1. Project Overview
This project aims to build an advanced, production-ready B2B lead generation pipeline. The system will scrape, enrich, and store business leads from diverse web sources. The core focus of the MVP is to establish a robust, stealthy, and highly accurate web crawling and scraping foundation, capable of handling various website structures effectively. Subsequent versions will build upon this core to incorporate advanced enrichment (including local LLM processing), sophisticated entity resolution, configurable targeting, and comprehensive status tracking.

MVP Goal: Create a fully functional and testable crawler and scraper system that can process a list of seed URLs, extract basic company information (company name, website, phone, email, address, description, social links), and operate with consideration for stealth and website politeness. Store extracted data simply.

2. Core Principles
Modularity: Each component (crawler, scraper, database, etc.) should be self-contained and have clear responsibilities, allowing for independent development, testing, and replacement.

Testability: Every piece of code should be testable. We will maintain comprehensive unit and integration tests. Test reports will be generated and reviewed.

Stealth & Politeness: The crawler must mimic human behavior to avoid detection and respect website resources. This includes User-Agent rotation, configurable delays, respecting robots.txt (to a practical extent for dynamic content), and readiness for proxy integration.

Robustness & Resilience: The system should handle common web errors gracefully, implement retries, and log issues effectively.

Extensibility: The architecture should make it easy to add new site-specific parsers, new enrichment strategies, and adapt to new target domains in the future.

Data Quality: Strive for accuracy in scraped data through careful selector design and validation.

Ethical Considerations: Prioritize ethical data sourcing, respecting privacy and website terms where possible.

Maintainability: Write clean, well-documented, and understandable code.

3. Module Status & Responsibilities (MVP Focus)
lead_gen_pipeline/config.py
Status: ✅ Complete & Tested

Responsibilities: Manages all application settings using pydantic-settings.BaseSettings, loads from .env and environment variables, provides structured settings objects, handles path resolution, supports nested configuration. Includes settings for crawler behavior (timeouts, Playwright, robots.txt), logging, and database connections.

lead_gen_pipeline/utils.py
Status: ✅ Complete & Tested

Functionality:

setup_logger(...): Configures and returns the Loguru logger instance.

Global logger instance: Initialized for application-wide logging.

@async_retry(...) decorator: Handles asynchronous retries with backoff and jitter.

Text/URL Utilities: clean_text, normalize_email, extract_emails_from_text, extract_domain (using tldextract), make_absolute_url.

DomainRateLimiter class & domain_rate_limiter instance: Manages request rate limiting per domain.

lead_gen_pipeline/crawler.py
Status: ✅ Complete & Tested (HTTPX, Playwright, Robots.txt)

Responsibilities: Fetches web page content using HTTPX or Playwright, respects robots.txt (configurable), handles retries, rate limiting, and basic proxy support. Returns HTML content, status code, and final URL.

Completed Functionality:

AsyncWebCrawler class structure.

HTTPX Path: _perform_httpx_fetch_attempt(...).

Playwright Path: _ensure_playwright_browser(), _get_playwright_page(), _fetch_with_playwright(), close_playwright_resources().

Robots.txt Handling: RobotsTxtDisallowedError, _fetch_and_parse_robots_txt(), _get_robots_parser() (with LRU cache), _check_robots_txt().

Common Fetch Logic: fetch_page_content(...), fetch_page(...).

User-Agent rotation, header construction, rate limiting, proxy support, basic CAPTCHA detection.

lead_gen_pipeline/scraper.py
Status: ✅ Basic Extraction Methods Complete & Tested

Responsibilities: Parses HTML content (using BeautifulSoup4) to extract structured data.

Completed Functionality (MVP):

HTMLScraper class initialized with HTML content and source URL.

Helper methods for text extraction and element finding.

extract_company_name(): Extracts from og:site_name or <title> with heuristics.

extract_phone_numbers(): Extracts from tel: links and page text using regex, with deduplication based on normalized numbers.

extract_emails(): Extracts from mailto: links and page text using utility function.

extract_addresses(): Basic extraction from schema.org PostalAddress and elements with common "address" classes.

extract_social_media_links(): Extracts links for common platforms.

extract_description(): Extracts from meta name="description" or og:description.

extract_canonical_url(): Extracts from <link rel="canonical">.

scrape(): Orchestrates all extraction methods and returns a dictionary of scraped data.

Next Steps for Scraper (Post-MVP/Enhancements): More robust address parsing, sophisticated company name extraction, industry extraction, site-specific parsers.

lead_gen_pipeline/database.py
Status: ⏳ To Do

Responsibilities (Planned): Handles all database interactions, including saving scraped data and potentially retrieving data for enrichment or deduplication.

Next Immediate Step: Define basic functions to store extracted lead data using SQLAlchemy with an async driver.

lead_gen_pipeline/models.py
Status: ⏳ To Do

Responsibilities (Planned): Defines the SQLAlchemy data models (e.g., for a Lead table) that map to the database schema.

Next Immediate Step: Define an initial Lead model corresponding to the data extracted by the scraper.

lead_gen_pipeline/llm_handler.py
Status: ⏳ To Do (Placeholder for MVP)

Responsibilities (Planned): Interface for local LLM interactions.

run_pipeline_mvp.py
Status: ⏳ To Do

Responsibilities (Planned): Orchestrates the MVP workflow: read seed URLs, crawl, scrape, store.

cli_mvp.py
Status: ⏳ To Do

Responsibilities (Planned): Basic Typer CLI for running the pipeline.

4. Coding Style & Conventions
PEP 8: Adhere strictly to PEP 8 Python style guidelines. Utilize a linter such as Flake8 or Ruff, configured to enforce these standards.

Type Hinting: Employ type hints for all function signatures, method parameters, return values, and variables where their type is not immediately obvious. This enhances code readability and enables static analysis tools.

Logging: Use the global logger instance configured in utils.py for all application logging. Log messages should be informative and use appropriate levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) to categorize events.

Docstrings: Write clear, concise docstrings for all modules, classes, public functions, and methods. Follow a consistent style (e.g., Google style: Args, Returns, Raises).

Comments:

Use comments to explain complex algorithms, non-obvious logic, or important decisions.

Include version/timestamp comments at the top of files for clarity during collaborative development (e.g., # Version: YYYY-MM-DD HH:MM UTC).

Avoid redundant comments that merely restate what the code does.

Configuration Over Hardcoding: All configurable parameters (API keys, timeouts, file paths, retry counts, etc.) must be managed through config.py and loaded from environment variables or .env files. Avoid hardcoding values directly in the application logic.

Asynchronous Code (async/await): Leverage asyncio for all I/O-bound operations, particularly in network requests (crawler) and potentially database interactions if using an async driver. Ensure non-blocking operations.

Error Handling: Implement robust error handling using try-except blocks. Catch specific exceptions where possible, log errors comprehensively, and handle them gracefully (e.g., retries, fallback mechanisms, or controlled failure).

Imports:

Organize imports at the top of each file, grouped into standard library, third-party, and then local application imports.

Use absolute imports for clarity where appropriate (e.g., from lead_gen_pipeline.module import name), and relative imports (from .module import name) for intra-package imports.

Naming Conventions:

Modules: lowercase_with_underscores.py

Packages: lowercase_with_underscores

Classes: CapWords

Functions & Methods: lowercase_with_underscores()

Constants: UPPERCASE_WITH_UNDERSCORES

Variables: lowercase_with_underscores

5. Testing Strategy
Framework: pytest will be used as the primary testing framework.

Plugins:

pytest-asyncio for testing asynchronous code.

pytest-mock (or unittest.mock) for creating mock objects.

pytest-cov for measuring test coverage.

pytest-html for generating user-friendly HTML test reports.

respx for mocking HTTPX requests in unit tests.

Unit Tests (tests/unit/):

Each module in lead_gen_pipeline/ (e.g., utils.py, crawler.py, scraper.py) will have a corresponding test file (e.g., test_utils.py, test_crawler.py, test_scraper.py) in the tests/unit/ directory.

Focus on testing individual functions, methods, and classes in isolation.

Employ mocking extensively to isolate the unit under test from external dependencies (network calls, file system, database, other modules).

Test edge cases, error conditions, and expected successful outcomes.

Integration Tests (tests/integration/):

Test the interaction between two or more components of the system (e.g., crawler fetching content and scraper parsing it; scraper outputting data and database storing it).

May involve a test database instance (e.g., in-memory SQLite) or carefully controlled external services (e.g., a local mock HTTP server, or very stable public test APIs like httpbin.org).

Minimize reliance on live, uncontrolled external websites for automated integration tests to avoid flakiness.

End-to-End (E2E) Tests (Future - Post-MVP):

Test the entire pipeline flow from URL input to data storage/output.

Will likely run against a small, curated set of diverse target websites or a dedicated staging environment that mimics real-world conditions.

These tests are crucial for validating the overall system behavior and stealth capabilities.

Test Coverage: Aim for high test coverage (e.g., >80-90%) for critical modules. Use pytest-cov to generate coverage reports and identify untested code paths.

Reporting: All automated test runs (especially in CI/CD) should generate clear HTML reports (using pytest-html) stored in reports/test_reports/. Each test function should have a descriptive name indicating what it tests.

Test Data: Use fixtures or helper functions to generate or load test data. For HTML parsing tests, small, representative mock HTML files can be stored in a test data directory.

6. Common Pitfalls to Avoid
Circular Imports: Design module dependencies carefully to prevent circular import errors.

Hardcoding Sensitive Information: API keys, passwords, and other secrets should never be hardcoded. Use environment variables and config.py.

Ignoring robots.txt (Completely): While our crawler has a toggle, be mindful of ethical considerations and website terms. Aggressively ignoring robots.txt can lead to IP bans.

Overly Aggressive Crawling: Implement and respect delays (DomainRateLimiter). Too many rapid requests can overload servers and lead to bans.

Brittle Selectors (for Scraping): Relying on highly specific CSS selectors that change frequently will break the scraper. Prioritize more robust selection strategies (semantic tags, stable IDs/classes, text content patterns).

Not Handling Errors Gracefully: Expect network issues, timeouts, unexpected HTML structures, and missing data. Implement try-except blocks, log errors, and allow the pipeline to continue or fail gracefully.

Blocking Operations in Async Code: Ensure all I/O operations (network, file system, database if using async driver) use await and non-blocking libraries to maintain the benefits of asyncio.

Global State Management: Minimize reliance on mutable global state. Pass data explicitly between functions and classes.

Resource Leaks: Ensure resources like browser instances (Playwright), database connections, and file handles are properly closed, especially in error conditions or long-running processes.

7. Full Vision Roadmap & Future Enhancements (Post-MVP)
I. Advanced Data Modeling & Deduplication:
* [ ] Implement PracticeLocation and ProfessionalOrGroup (or similar) models for nuanced entity representation.
* [ ] Develop robust company/entity deduplication logic in database.py (fuzzy matching on name/address, website normalization, phone number normalization).
* [ ] Implement strategies for merging data from multiple sources for the same entity, prioritizing more reliable sources.
* [ ] Add fields for confidence scores for individual data points and overall entity match.

II. Sophisticated Enrichment & LLM Integration:
* [ ] Fully integrate local LLM (llm_handler.py) for:
* Entity type classification (HQ, branch, owner-op, franchise).
* Service/specialty identification based on configurable target profiles.
* Extraction of key personnel and their roles.
* Sentiment analysis or business focus identification from text.
* Verification of business activity/status.
* [ ] Develop configurable target_profile.yaml (or similar) for defining scraping/enrichment goals, keywords, and LLM prompt components for different campaigns.
* [ ] Implement the dynamic scoring system in an enricher.py module based on target profile, scraped data, and LLM output.
* [ ] Explore web archive lookups (e.g., Wayback Machine) or WHOIS data for domain age/history.
* [ ] (Optional) Reverse image search for logo detection.

III. Intelligent Crawling & Status Tracking:
* [ ] Implement robust robots.txt parsing and adherence using a dedicated library (already done with urllib.robotparser, but could explore alternatives like reppy for more features if needed).
* [ ] Implement sitemap.xml parsing for guided and more efficient crawling.
* [ ] Develop heuristics for prioritizing link following within a site (e.g., "about," "contact," "services," "locations," "team").
* [ ] Add configurable crawl depth and scope (e.g., stay within domain, follow specific outbound links).
* [ ] Implement robust business status tracking (active_confirmed, inactive_confirmed_manual, inactive_likely_auto, status_unknown) in the database with timestamps and source of status.
* [ ] Create logic/module for periodically checking business status (HTTP checks, content keyword checks, LLM verification).
* [ ] Develop a system for manual overrides and review of business status and lead data.
* [ ] Implement an efficient re-crawl strategy (check last_scraped_at, conditional re-scraping based on change detection or schedule).

IV. Enhanced Stealth & Operational Robustness:
* [ ] Full Playwright integration with advanced stealth techniques (e.g., playwright-stealth patterns, canvas fingerprinting countermeasures, WebGL spoofing, timezone/locale consistency).
* [ ] Sophisticated proxy management: support for rotating proxies (e.g., BrightData, ScraperAPI integration via config.py), proxy health checks, automatic rotation on failure.
* [ ] CAPTCHA solving service integration (e.g., 2Captcha) triggered when CAPTCHAs are detected.
* [ ] Dynamic delay adjustments based on server response times or error rates per domain.
* [ ] More sophisticated error categorization and specific retry strategies for different error types.
* [ ] User-Agent generation based on real-world distributions.
* [ ] Viewport and screen resolution randomization for Playwright.

V. User Interface & Operations:
* [ ] Full-featured CLI (cli.py using Typer) for:
* Managing pipeline runs (start, stop, status).
* Ingesting target URL lists (CSV, text files).
* Managing target profiles.
* Manually overriding business status or lead data.
* Exporting data in various formats (CSV, JSON, Parquet).
* Viewing pipeline statistics and error reports.
* [ ] Optional FastAPI layer for a web interface to:
* View and query collected lead data.
* Manage targets and profiles.
* Monitor pipeline runs and health.
* Trigger manual enrichments or re-scrapes.
* [ ] Dashboarding/reporting on pipeline performance, lead acquisition rates, data quality metrics.
* [ ] Slack/Discord notifications for critical errors or successful run completions.

VI. Deployment & Scalability:
* [ ] Mature Dockerfile and docker-compose.yml for production deployment (including database service if needed).
* [ ] Exploration and potential implementation of distributed task queues (e.g., Celery with Redis/RabbitMQ) for scaling out crawling, scraping, and enrichment tasks across multiple workers/machines.
* [ ] Strategies for cloud deployment (e.g., GCP, AWS) with considerations for scalable compute, storage, and networking.
* [ ] Database schema migration management using Alembic.

This document will evolve as we build. Let's keep it updated.

---

## 5. Current Python Code Files & Other Key Files

### 5.1. `lead_gen_pipeline/config.py`
```python
# lead_gen_pipeline/config.py
# Version: 2025-05-23 16:30 EDT
import os
from pathlib import Path
from typing import List, Optional, Union

from pydantic import (
    HttpUrl,
    DirectoryPath,
    FilePath,
    field_validator,
    ValidationInfo,
    Field
)
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class CrawlerSettings(BaseSettings):
    """Settings specific to the crawler component."""
    model_config = SettingsConfigDict(env_prefix='CRAWLER_', extra='ignore', case_sensitive=False)

    USER_AGENTS: List[str] = Field(
        default=[
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
        ]
    )
    DEFAULT_TIMEOUT_SECONDS: int = Field(default=30, ge=5, le=120)
    MIN_DELAY_PER_DOMAIN_SECONDS: float = Field(default=3.0, ge=0.5)
    MAX_DELAY_PER_DOMAIN_SECONDS: float = Field(default=10.0, ge=1.0)
    MAX_RETRIES: int = Field(default=3, ge=0)
    BACKOFF_FACTOR: float = Field(default=0.8, ge=0.1) # For async_retry initial delay, not directly used by crawler's internal delay logic
    USE_PLAYWRIGHT_BY_DEFAULT: bool = Field(default=False)
    PLAYWRIGHT_HEADLESS_MODE: bool = Field(default=True)
    HTTP_PROXY_URL: Optional[HttpUrl] = Field(default=None)
    HTTPS_PROXY_URL: Optional[HttpUrl] = Field(default=None)

    # Robots.txt settings
    RESPECT_ROBOTS_TXT: bool = Field(default=True, description="Whether to fetch and respect robots.txt rules.")
    ROBOTS_TXT_USER_AGENT: str = Field(
        default="*",
        description="User agent string to use when checking robots.txt. '*' respects rules for all user agents."
    )
    ROBOTS_TXT_CACHE_SIZE: int = Field(default=100, ge=10, le=1000, description="Maximum number of compiled robots.txt parsers to keep in memory.")
    ROBOTS_TXT_FETCH_TIMEOUT_SECONDS: int = Field(default=10, ge=3, le=60, description="Timeout for fetching robots.txt files.")


    @field_validator('MAX_DELAY_PER_DOMAIN_SECONDS')
    @classmethod
    def max_delay_must_be_greater_than_min_delay(cls, v: float, info: ValidationInfo) -> float:
        if 'MIN_DELAY_PER_DOMAIN_SECONDS' in info.data and v < info.data['MIN_DELAY_PER_DOMAIN_SECONDS']:
            raise ValueError('MAX_DELAY_PER_DOMAIN_SECONDS must be >= MIN_DELAY_PER_DOMAIN_SECONDS')
        return v

class LoggingSettings(BaseSettings):
    """Settings for application logging."""
    model_config = SettingsConfigDict(env_prefix='LOGGING_', extra='ignore', case_sensitive=False)

    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE_PATH: Path = Field(default_factory=lambda: BASE_DIR / "logs" / "app.log")
    ERROR_LOG_FILE_PATH: Path = Field(default_factory=lambda: BASE_DIR / "logs" / "error.log")
    LOG_ROTATION_SIZE: str = Field(default="10 MB")
    LOG_RETENTION_POLICY: str = Field(default="7 days")

    @field_validator('LOG_FILE_PATH', 'ERROR_LOG_FILE_PATH', mode='before')
    @classmethod
    def ensure_log_dir_exists(cls, v: Union[str, Path], info: ValidationInfo) -> Path:
        log_path = Path(v)
        if not log_path.is_absolute():
            log_path = BASE_DIR / log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return log_path.resolve()

class DatabaseSettings(BaseSettings):
    """Settings for the database connection."""
    model_config = SettingsConfigDict(env_prefix='DATABASE_', extra='ignore', case_sensitive=False)

    DATABASE_URL: str = Field(default_factory=lambda: f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'leads_mvp.db'}")
    ECHO_SQL: bool = Field(default=False)

    @field_validator('DATABASE_URL', mode='before')
    @classmethod
    def ensure_db_dir_exists(cls, v: str, info: ValidationInfo) -> str:
        if v.startswith("sqlite") or v.startswith("sqlite+aiosqlite"):
            parts = v.split(":///", 1)
            if len(parts) < 2:
                return v
            db_path_str = parts[1]
            db_path = Path(db_path_str)
            if not db_path.is_absolute():
                db_path = BASE_DIR / db_path
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"{parts[0]}:///{db_path.resolve()}"
        return v

class AppSettings(BaseSettings):
    """Main application settings, composing other settings groups."""
    model_config = SettingsConfigDict(
        env_file=Path(os.getenv("ENV_FILE_PATH", BASE_DIR / ".env")),
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False,
        env_nested_delimiter='__'
    )

    PROJECT_NAME: str = Field(default="B2B Lead Generation Pipeline")
    BASE_DIR: DirectoryPath = Field(default=BASE_DIR)
    INPUT_URLS_CSV: FilePath = Field(default_factory=lambda: BASE_DIR / "data" / "urls_seed.csv")

    crawler: CrawlerSettings = CrawlerSettings()
    logging: LoggingSettings = LoggingSettings()
    database: DatabaseSettings = DatabaseSettings()

    MAX_PIPELINE_CONCURRENCY: int = Field(default=5, ge=1)
    MAX_CONCURRENT_REQUESTS_PER_DOMAIN: int = Field(default=1, ge=1)

try:
    settings = AppSettings()
except Exception as e:
    print(f"CRITICAL: Error loading application settings: {e}")
    print("CRITICAL: Falling back to default settings. Check your .env file and configuration.")
    settings = AppSettings(
        crawler=CrawlerSettings(),
        logging=LoggingSettings(),
        database=DatabaseSettings(),
        _env_file=None # type: ignore [call-arg] # To satisfy pydantic if _env_file is expected
    )


```

### 5.2. `tests/unit/test_config.py`
```python
# tests/unit/test_config.py
# Version: 2025-05-23 16:30 EDT
import os
import pytest
from pathlib import Path
import sys

PROJECT_ROOT_FOR_IMPORTS = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORTS))

from pydantic import ValidationError
from lead_gen_pipeline.config import AppSettings, CrawlerSettings, LoggingSettings, DatabaseSettings

TEST_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

@pytest.fixture(scope="function")
def temp_env_vars_for_override(monkeypatch):
    """Fixture to temporarily set OS environment variables for override tests."""
    env_vars_to_set = {
        "PROJECT_NAME": "Test Project From OS Env Override",
        "LOGGING__LOG_LEVEL": "DEBUG",
        "DATABASE__DATABASE_URL": f"sqlite+aiosqlite:///{TEST_PROJECT_ROOT / 'db_from_os_env_override.db'}",
        "CRAWLER__DEFAULT_TIMEOUT_SECONDS": "50",
        "CRAWLER__RESPECT_ROBOTS_TXT": "false", # Test boolean override
        "CRAWLER__ROBOTS_TXT_USER_AGENT": "TestBot/1.0",
        "CRAWLER__ROBOTS_TXT_CACHE_SIZE": "50",
        "CRAWLER__ROBOTS_TXT_FETCH_TIMEOUT_SECONDS": "5",
        "MAX_PIPELINE_CONCURRENCY": "15"
    }
    for k, v in env_vars_to_set.items():
        monkeypatch.setenv(k, str(v))
    yield env_vars_to_set
    # No need to cleanup, monkeypatch handles it

@pytest.fixture(scope="function")
def temp_dot_env_file_for_override(tmp_path):
    """Fixture to create a temporary .env file for override testing."""
    env_content = f"""
PROJECT_NAME="Project From Temp DotEnv File Override"
LOGGING__LOG_LEVEL="WARNING"
DATABASE__DATABASE_URL="sqlite+aiosqlite:///{tmp_path}/db_from_temp_dotenv_override.db"
CRAWLER__DEFAULT_TIMEOUT_SECONDS="55"
CRAWLER__RESPECT_ROBOTS_TXT=true
CRAWLER__ROBOTS_TXT_USER_AGENT="DotEnvBot/2.0"
CRAWLER__ROBOTS_TXT_CACHE_SIZE="150"
CRAWLER__ROBOTS_TXT_FETCH_TIMEOUT_SECONDS="15"
MAX_PIPELINE_CONCURRENCY="18"
INPUT_URLS_CSV="{tmp_path}/custom_urls.csv"
    """
    dot_env_path = tmp_path / ".env.test_override"
    dot_env_path.write_text(env_content)
    (tmp_path / "custom_urls.csv").touch()
    return dot_env_path

def test_default_settings_load_correctly():
    """Test that AppSettings loads with default values when no .env or OS env vars affect it."""
    settings = AppSettings(_env_file=None) # type: ignore [call-arg]

    assert settings.PROJECT_NAME == "B2B Lead Generation Pipeline"
    assert settings.BASE_DIR == TEST_PROJECT_ROOT
    assert settings.INPUT_URLS_CSV.resolve() == (TEST_PROJECT_ROOT / "data" / "urls_seed.csv").resolve()
    
    assert settings.logging.LOG_LEVEL == "INFO"
    assert settings.logging.LOG_FILE_PATH.resolve() == (TEST_PROJECT_ROOT / "logs" / "app.log").resolve()
    assert settings.logging.LOG_FILE_PATH.parent.exists()

    # Crawler default settings
    assert settings.crawler.DEFAULT_TIMEOUT_SECONDS == 30
    assert settings.crawler.HTTP_PROXY_URL is None
    assert settings.crawler.RESPECT_ROBOTS_TXT is True # Default is True
    assert settings.crawler.ROBOTS_TXT_USER_AGENT == "*" # Default is "*"
    assert settings.crawler.ROBOTS_TXT_CACHE_SIZE == 100
    assert settings.crawler.ROBOTS_TXT_FETCH_TIMEOUT_SECONDS == 10


    expected_db_path = (TEST_PROJECT_ROOT / "data" / "leads_mvp.db").resolve()
    assert settings.database.DATABASE_URL == f"sqlite+aiosqlite:///{expected_db_path}"
    assert Path(expected_db_path).parent.exists()
    assert settings.database.ECHO_SQL is False
    assert settings.MAX_PIPELINE_CONCURRENCY == 5

def test_settings_override_with_env_variables(temp_env_vars_for_override):
    """Test that settings can be overridden by OS environment variables."""
    current_settings = AppSettings(_env_file=None) # type: ignore [call-arg] # Ignore any actual .env file

    assert current_settings.PROJECT_NAME == "Test Project From OS Env Override"
    assert current_settings.logging.LOG_LEVEL == "DEBUG"
    assert current_settings.crawler.DEFAULT_TIMEOUT_SECONDS == 50
    
    # Test new crawler settings override
    assert current_settings.crawler.RESPECT_ROBOTS_TXT is False # 'false' string becomes False boolean
    assert current_settings.crawler.ROBOTS_TXT_USER_AGENT == "TestBot/1.0"
    assert current_settings.crawler.ROBOTS_TXT_CACHE_SIZE == 50
    assert current_settings.crawler.ROBOTS_TXT_FETCH_TIMEOUT_SECONDS == 5


    expected_db_path = (TEST_PROJECT_ROOT / "db_from_os_env_override.db").resolve()
    assert current_settings.database.DATABASE_URL == f"sqlite+aiosqlite:///{expected_db_path}"
    assert Path(expected_db_path).parent.exists()
    assert current_settings.MAX_PIPELINE_CONCURRENCY == 15

def test_settings_override_with_dotenv_file(temp_dot_env_file_for_override):
    """Test that settings can be overridden by a specific .env file."""
    current_settings = AppSettings(_env_file=temp_dot_env_file_for_override)

    assert current_settings.PROJECT_NAME == "Project From Temp DotEnv File Override"
    assert current_settings.logging.LOG_LEVEL == "WARNING"
    expected_db_path_dotenv = (temp_dot_env_file_for_override.parent / "db_from_temp_dotenv_override.db").resolve()
    assert current_settings.database.DATABASE_URL == f"sqlite+aiosqlite:///{expected_db_path_dotenv}"
    assert Path(expected_db_path_dotenv).parent.exists()
    assert current_settings.crawler.DEFAULT_TIMEOUT_SECONDS == 55
    
    # Test new crawler settings override from .env file
    assert current_settings.crawler.RESPECT_ROBOTS_TXT is True # 'true' string becomes True
    assert current_settings.crawler.ROBOTS_TXT_USER_AGENT == "DotEnvBot/2.0"
    assert current_settings.crawler.ROBOTS_TXT_CACHE_SIZE == 150
    assert current_settings.crawler.ROBOTS_TXT_FETCH_TIMEOUT_SECONDS == 15

    assert current_settings.MAX_PIPELINE_CONCURRENCY == 18
    expected_csv_path = (temp_dot_env_file_for_override.parent / "custom_urls.csv").resolve()
    assert current_settings.INPUT_URLS_CSV.resolve() == expected_csv_path

def test_crawler_delay_validation():
    """Test validation for crawler min/max delay."""
    with pytest.raises(ValueError, match="MAX_DELAY_PER_DOMAIN_SECONDS must be >= MIN_DELAY_PER_DOMAIN_SECONDS"):
        CrawlerSettings(MIN_DELAY_PER_DOMAIN_SECONDS=5.0, MAX_DELAY_PER_DOMAIN_SECONDS=2.0)
    try:
        CrawlerSettings(MIN_DELAY_PER_DOMAIN_SECONDS=2.0, MAX_DELAY_PER_DOMAIN_SECONDS=5.0)
    except ValueError:
        pytest.fail("Valid delay settings raised ValueError")

def test_log_path_creation(tmp_path, monkeypatch):
    """Test that log directories are created when settings are loaded with custom paths from .env."""
    dot_env_path = tmp_path / ".env.logtest"
    relative_log_path = "./my_custom_temp_logs/app_via_env.log"
    dot_env_path.write_text(f"LOGGING__LOG_FILE_PATH=\"{relative_log_path}\"\n")
    
    settings_with_temp_log = AppSettings(_env_file=dot_env_path)
    
    expected_log_file = (TEST_PROJECT_ROOT / Path(relative_log_path)).resolve()

    assert settings_with_temp_log.logging.LOG_FILE_PATH.resolve() == expected_log_file
    assert expected_log_file.parent.exists()

def test_db_path_creation_sqlite(tmp_path, monkeypatch):
    """Test that SQLite DB directory is handled correctly by AppSettings when path is from .env."""
    dot_env_path = tmp_path / ".env.dbtest"
    relative_db_path = "./my_test_data_dir_from_env/test_database.db"
    dot_env_path.write_text(f"DATABASE__DATABASE_URL=\"sqlite+aiosqlite:///{relative_db_path}\"\n")

    settings_with_relative_db = AppSettings(_env_file=dot_env_path)
    
    expected_db_file = (TEST_PROJECT_ROOT / Path(relative_db_path)).resolve()

    assert settings_with_relative_db.database.DATABASE_URL == f"sqlite+aiosqlite:///{expected_db_file}"
    assert expected_db_file.parent.exists()

if __name__ == "__main__":
    pytest.main([__file__])

```

### 5.3. `lead_gen_pipeline/utils.py`
```python
# lead_gen_pipeline/utils.py
# Version: 2025-05-22 20:45 UTC 
import sys
import asyncio
import random
import time 
import re 
from functools import wraps 
from typing import Optional, Callable, Any, Coroutine, List 
from urllib.parse import urlparse, urljoin 
import tldextract 

from loguru import logger

try:
    from .config import LoggingSettings, AppSettings, settings as global_app_settings
except ImportError:
    from lead_gen_pipeline.config import LoggingSettings, AppSettings, settings as global_app_settings


def setup_logger(custom_logging_settings: Optional[LoggingSettings] = None) -> logger:
    """
    Configures and returns the Loguru logger instance.
    """
    current_settings = custom_logging_settings if custom_logging_settings is not None else global_app_settings.logging

    logger.remove() 

    logger.add(
        sys.stderr,
        level=current_settings.LOG_LEVEL.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
        enqueue=True
    )

    if current_settings.LOG_FILE_PATH: 
        current_settings.LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(current_settings.LOG_FILE_PATH), 
            rotation=current_settings.LOG_ROTATION_SIZE,
            retention=current_settings.LOG_RETENTION_POLICY,
            level=current_settings.LOG_LEVEL.upper(),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            enqueue=True,
        )

    if current_settings.ERROR_LOG_FILE_PATH: 
        current_settings.ERROR_LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(current_settings.ERROR_LOG_FILE_PATH), 
            rotation=current_settings.LOG_ROTATION_SIZE,
            retention=current_settings.LOG_RETENTION_POLICY,
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            enqueue=True,
        )
    
    return logger

logger = setup_logger()

# --- Async Retry Decorator ---
def async_retry(
    max_retries_override: Optional[int] = None, # Renamed for clarity
    delay_seconds: float = 1.0,
    backoff_factor: float = 2.0,
    jitter_factor: float = 0.5,
    exceptions: tuple = (Exception,),
    retry_logger: Optional[logger] = None
):
    """
    Asynchronous retry decorator with exponential backoff and jitter.
    MAX_RETRIES is read at call time from global settings if not overridden.
    """
    
    _logger = retry_logger if retry_logger is not None else logger

    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Determine effective_max_retries at call time
            current_max_retries = max_retries_override
            if current_max_retries is None:
                try:
                    current_max_retries = global_app_settings.crawler.MAX_RETRIES
                except AttributeError: 
                    _logger.warning("Could not read MAX_RETRIES from settings for retry, defaulting to 3.")
                    current_max_retries = 3
            
            current_delay = delay_seconds
            # Loop for initial attempt (0) + number of retries
            for attempt in range(current_max_retries + 1): 
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == current_max_retries: # Last attempt failed
                        _logger.error(
                            f"Function '{func.__name__}' failed after {current_max_retries + 1} attempts. Last error: {type(e).__name__}: {e}"
                        )
                        raise # Re-raise the last exception

                    # Calculate jitter for the current delay
                    jitter = random.uniform(-jitter_factor, jitter_factor) * current_delay
                    actual_sleep_time = max(0, current_delay + jitter) # Ensure sleep time is not negative

                    _logger.warning(
                        f"Attempt {attempt + 1}/{current_max_retries + 1} for '{func.__name__}' failed with {type(e).__name__}: {e}. "
                        f"Retrying in {actual_sleep_time:.2f}s (delay: {current_delay:.2f}s, jitter: {jitter:.2f}s)..."
                    )
                    
                    await asyncio.sleep(actual_sleep_time)
                    current_delay *= backoff_factor # Increase delay for next potential retry
            # This line should be unreachable if logic is correct and an exception is always raised on final failure.
            # However, to satisfy linters/type checkers that expect a return value:
            _logger.critical(f"Reached unexpected end of retry wrapper for {func.__name__}. This should not happen.")
            return None # Should be unreachable
        return wrapper
    return decorator

# --- Text Cleaning & Normalization ---
def clean_text(text: Optional[str]) -> Optional[str]:
    if text is None: return None
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return text if text else None

EMAIL_REGEX_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
COMPILED_EMAIL_REGEX = re.compile(EMAIL_REGEX_PATTERN)

def normalize_email(email: Optional[str]) -> Optional[str]:
    if email is None: return None
    email = email.lower().strip()
    match = COMPILED_EMAIL_REGEX.fullmatch(email)
    return email if match else None

def extract_emails_from_text(text: Optional[str]) -> List[str]:
    if not text: return []
    found_emails = COMPILED_EMAIL_REGEX.findall(text)
    normalized_emails = sorted(list(set(normalize_email(email) for email in found_emails if normalize_email(email))))
    return normalized_emails

# --- URL Parsing & Manipulation ---
def extract_domain(url: Optional[str], include_subdomain: bool = False) -> Optional[str]:
    if not url: return None
    parsed_original_scheme = urlparse(url)
    if parsed_original_scheme.scheme.lower() in ('mailto', 'tel'): return None
    ext = tldextract.extract(url)
    if not ext.suffix: 
        parsed_url_for_ip = urlparse(url if "://" in url else "http://" + url)
        if parsed_url_for_ip.hostname:
            ip_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
            if re.match(ip_pattern, parsed_url_for_ip.hostname) or parsed_url_for_ip.hostname.lower() == "localhost":
                return parsed_url_for_ip.hostname 
        return None 
    if include_subdomain:
        if ext.subdomain:
            return f"{ext.subdomain}.{ext.domain}.{ext.suffix}"
        else:
            return f"{ext.domain}.{ext.suffix}"
    else: 
        return f"{ext.domain}.{ext.suffix}"

def make_absolute_url(base_url: str, relative_or_absolute_url: Optional[str]) -> Optional[str]:
    if not relative_or_absolute_url: return None
    processed_url = relative_or_absolute_url.strip()
    if not processed_url: return base_url 
    if urlparse(processed_url).scheme: return processed_url
    try:
        return urljoin(base_url, processed_url)
    except ValueError:
        logger.warning(f"Could not join base_url '{base_url}' and relative_url '{processed_url}'")
        return None

# --- Domain Rate Limiter Class ---
class DomainRateLimiter:
    def __init__(self):
        self._domain_locks: dict[str, asyncio.Lock] = {} 
        self._last_request_time: dict[str, float] = {}
        self._domain_semaphores: dict[str, asyncio.Semaphore] = {}
        logger.info("DomainRateLimiter initialized.")

    def _get_or_create_domain_specific_locks(self, domain: str):
        if domain not in self._domain_locks:
            self._domain_locks[domain] = asyncio.Lock()
            try:
                concurrency = global_app_settings.MAX_CONCURRENT_REQUESTS_PER_DOMAIN
            except AttributeError:
                logger.warning("MAX_CONCURRENT_REQUESTS_PER_DOMAIN not found in global_app_settings, defaulting to 1.")
                concurrency = 1
            self._domain_semaphores[domain] = asyncio.Semaphore(concurrency)
            self._last_request_time[domain] = 0.0 

    async def acquire(self, domain: str) -> None:
        self._get_or_create_domain_specific_locks(domain)
        domain_semaphore = self._domain_semaphores[domain]
        await domain_semaphore.acquire() 
        async with self._domain_locks[domain]: 
            current_time = time.monotonic()
            time_since_last = current_time - self._last_request_time.get(domain, 0.0)
            try:
                min_delay = global_app_settings.crawler.MIN_DELAY_PER_DOMAIN_SECONDS
                max_delay = global_app_settings.crawler.MAX_DELAY_PER_DOMAIN_SECONDS
            except AttributeError:
                logger.warning("Delay settings (MIN/MAX_DELAY_PER_DOMAIN_SECONDS) not found in global_app_settings.crawler, using defaults for DomainRateLimiter.")
                min_delay = 1.0 
                max_delay = 5.0 
            required_delay = random.uniform(min_delay, max_delay)
            if time_since_last < required_delay:
                sleep_duration = required_delay - time_since_last
                logger.debug(
                    f"Rate limiting domain '{domain}': sleeping for {sleep_duration:.2f}s. "
                    f"(Required: {required_delay:.2f}s, Actual since last: {time_since_last:.2f}s)"
                )
                await asyncio.sleep(sleep_duration)
            self._last_request_time[domain] = time.monotonic()

    def release(self, domain: str) -> None:
        if domain in self._domain_semaphores:
            self._domain_semaphores[domain].release()
            logger.trace(f"Released permit for domain '{domain}'.") 
        else:
            logger.warning(f"Attempted to release permit for unmanaged domain '{domain}'.")

    async def wait_for_domain(self, domain: str) -> "DomainRateLimiterContextManager":
        await self.acquire(domain)
        return DomainRateLimiterContextManager(self, domain)

class DomainRateLimiterContextManager:
    def __init__(self, limiter: DomainRateLimiter, domain: str):
        self._limiter = limiter
        self._domain = domain
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._limiter.release(self._domain)

domain_rate_limiter = DomainRateLimiter()

def example_utility_function():
    logger.info("example_utility_function called from utils.py")
    return True

```

### 5.4. `tests/unit/test_utils.py`
```python
# tests/unit/test_utils.py
# Version: 2025-05-22 21:15 UTC 
import pytest
import sys
from pathlib import Path
import time 
import os 
import asyncio 
from unittest.mock import AsyncMock, call 

PROJECT_ROOT_FOR_IMPORTS = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORTS))

from lead_gen_pipeline.utils import (
    setup_logger, 
    example_utility_function, 
    async_retry, 
    logger as utils_logger,
    clean_text,
    normalize_email,
    extract_emails_from_text,
    extract_domain,
    make_absolute_url,
    DomainRateLimiter, 
    domain_rate_limiter # Import the global instance if testing it, or new instances
)
from lead_gen_pipeline.config import LoggingSettings, AppSettings, settings as global_app_settings, CrawlerSettings

@pytest.fixture(scope="function")
def test_logger_instance(tmp_path):
    temp_log_file = tmp_path / "test_app.log"
    temp_error_log_file = tmp_path / "test_error.log"
    test_logging_settings = LoggingSettings(
        LOG_LEVEL="DEBUG", 
        LOG_FILE_PATH=temp_log_file,
        ERROR_LOG_FILE_PATH=temp_error_log_file,
    )
    setup_logger(custom_logging_settings=test_logging_settings)
    yield utils_logger, temp_log_file, temp_error_log_file
    setup_logger() # Reset to default config

# --- Logging Tests ---
# [Keep all existing logging tests as they were, they are correct]
def test_logger_writes_to_app_log(test_logger_instance):
    logger, temp_log_file, _ = test_logger_instance
    unique_message = f"Test info message for app log @ {time.time()}"
    logger.info(unique_message)
    logger.complete() 
    with open(temp_log_file, "r") as f:
        log_content = f.read()
    assert unique_message in log_content
    assert "INFO" in log_content

def test_logger_writes_to_error_log(test_logger_instance):
    logger, _, temp_error_log_file = test_logger_instance
    unique_message = f"Test error message for error log @ {time.time()}"
    logger.error(unique_message)
    logger.complete()
    with open(temp_error_log_file, "r") as f:
        log_content = f.read()
    assert unique_message in log_content
    assert "ERROR" in log_content

def test_logger_debug_messages_logged_when_level_is_debug(tmp_path):
    temp_log_file = tmp_path / "debug_test_app.log"
    debug_logging_settings = LoggingSettings(
        LOG_LEVEL="DEBUG",
        LOG_FILE_PATH=temp_log_file,
        ERROR_LOG_FILE_PATH=tmp_path / "debug_test_error.log" 
    )
    logger = setup_logger(custom_logging_settings=debug_logging_settings)
    debug_message = f"This is a DEBUG message @ {time.time()}"
    logger.debug(debug_message)
    logger.complete()
    with open(temp_log_file, "r") as f:
        log_content = f.read()
    assert debug_message in log_content
    assert "DEBUG" in log_content

def test_logger_debug_messages_not_logged_when_level_is_info(tmp_path):
    temp_log_file = tmp_path / "info_test_app.log"
    info_logging_settings = LoggingSettings(
        LOG_LEVEL="INFO",
        LOG_FILE_PATH=temp_log_file,
        ERROR_LOG_FILE_PATH=tmp_path / "info_test_error.log" 
    )
    logger = setup_logger(custom_logging_settings=info_logging_settings)
    debug_message = f"This is a DEBUG message (should not be logged) @ {time.time()}"
    info_message = f"This is an INFO message (should be logged) @ {time.time()}"
    logger.debug(debug_message)
    logger.info(info_message) 
    logger.complete()
    with open(temp_log_file, "r") as f:
        log_content = f.read()
    assert debug_message not in log_content
    assert info_message in log_content 

def test_example_utility_function_logs_and_returns_true(test_logger_instance):
    logger, temp_log_file, _ = test_logger_instance 
    result = example_utility_function() 
    assert result is True
    logger.complete()
    with open(temp_log_file, "r") as f:
        log_content = f.read()
    assert "example_utility_function called from utils.py" in log_content

def test_setup_logger_with_global_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGGING__LOG_LEVEL", "WARNING")
    temp_global_log_path_str = str(tmp_path / "global_app_test.log")
    monkeypatch.setenv("LOGGING__LOG_FILE_PATH", temp_global_log_path_str)
    temp_global_error_log_path_str = str(tmp_path / "global_error_test.log")
    monkeypatch.setenv("LOGGING__ERROR_LOG_FILE_PATH", temp_global_error_log_path_str)

    current_app_settings = AppSettings(_env_file=None) 
    logger = setup_logger(custom_logging_settings=current_app_settings.logging)
    
    assert current_app_settings.logging.LOG_LEVEL == "WARNING"
    assert current_app_settings.logging.LOG_FILE_PATH.resolve() == Path(temp_global_log_path_str).resolve()
    assert current_app_settings.logging.ERROR_LOG_FILE_PATH.resolve() == Path(temp_global_error_log_path_str).resolve()

    info_message = f"Global INFO (should NOT be logged by WARNING level) @ {time.time()}"
    warning_message = f"Global WARNING (should be logged) @ {time.time()}"
    debug_message = f"Global DEBUG (should NOT be logged by WARNING level) @ {time.time()}"

    logger.info(info_message) 
    logger.warning(warning_message)
    logger.debug(debug_message)
    logger.complete()

    with open(current_app_settings.logging.LOG_FILE_PATH, "r") as f:
        log_content = f.read()
    
    assert info_message not in log_content
    assert warning_message in log_content
    assert debug_message not in log_content

# --- Tests for async_retry decorator ---
# [Keep all existing async_retry tests as they were]
class CustomRetryException(Exception): pass
class AnotherRetryException(Exception): pass

@pytest.mark.asyncio
async def test_async_retry_succeeds_on_first_try(test_logger_instance):
    logger, temp_log_file, _ = test_logger_instance
    @async_retry(max_retries=2, delay_seconds=0.01, retry_logger=logger)
    async def func_succeeds(): return "success"
    result = await func_succeeds()
    assert result == "success"
    logger.complete()
    with open(temp_log_file, "r") as f: log_content = f.read()
    assert "Retrying in" not in log_content

@pytest.mark.asyncio
async def test_async_retry_succeeds_after_failures(test_logger_instance):
    logger, temp_log_file, _ = test_logger_instance
    mock_func = AsyncMock()
    mock_func.side_effect = [CustomRetryException("Attempt 1 fails"), CustomRetryException("Attempt 2 fails"), "success"]
    @async_retry(max_retries=2, delay_seconds=0.01, exceptions=(CustomRetryException,), retry_logger=logger)
    async def func_to_retry(): return await mock_func()
    result = await func_to_retry()
    assert result == "success"
    assert mock_func.call_count == 3
    logger.complete()
    with open(temp_log_file, "r") as f: log_content = f.read()
    assert "Retrying in" in log_content
    assert "Attempt 1/3" in log_content 
    assert "Attempt 2/3" in log_content 

@pytest.mark.asyncio
async def test_async_retry_fails_after_max_retries(test_logger_instance):
    logger, temp_log_file, temp_error_log_file = test_logger_instance
    mock_func = AsyncMock(side_effect=CustomRetryException("Always fails"))
    @async_retry(max_retries=2, delay_seconds=0.01, exceptions=(CustomRetryException,), retry_logger=logger)
    async def func_always_fails(): return await mock_func()
    with pytest.raises(CustomRetryException, match="Always fails"):
        await func_always_fails()
    assert mock_func.call_count == 3 
    logger.complete()
    with open(temp_log_file, "r") as f: log_content = f.read()
    assert "Retrying in" in log_content
    with open(temp_error_log_file, "r") as f: error_log_content = f.read()
    assert "failed after 3 attempts" in error_log_content

@pytest.mark.asyncio
async def test_async_retry_uses_default_max_retries_from_settings(monkeypatch, test_logger_instance):
    logger, temp_log_file, _ = test_logger_instance
    from lead_gen_pipeline.config import settings as app_config_settings # Ensure we get the live settings
    monkeypatch.setattr(app_config_settings.crawler, 'MAX_RETRIES', 1)
    
    mock_func = AsyncMock()
    mock_func.side_effect = [CustomRetryException("Fail 1"), "Success on 2nd call"]
    @async_retry(delay_seconds=0.01, exceptions=(CustomRetryException,), retry_logger=logger) 
    async def func_uses_settings_retries(): return await mock_func()
    result = await func_uses_settings_retries()
    assert result == "Success on 2nd call"
    assert mock_func.call_count == 2 
    logger.complete()
    with open(temp_log_file, "r") as f: log_content = f.read()
    assert "Attempt 1/2" in log_content 

@pytest.mark.asyncio
async def test_async_retry_only_catches_specified_exceptions(test_logger_instance):
    logger, _, _ = test_logger_instance
    mock_func = AsyncMock(side_effect=ValueError("This is a ValueError"))
    @async_retry(max_retries=1, delay_seconds=0.01, exceptions=(CustomRetryException,), retry_logger=logger)
    async def func_specific_exception(): return await mock_func()
    with pytest.raises(ValueError, match="This is a ValueError"):
        await func_specific_exception()
    assert mock_func.call_count == 1

# --- Text/URL Utilities Tests (Keep existing ones) ---
@pytest.mark.parametrize("text_input, expected_output", [
    ("  hello world  ", "hello world"), ("hello   world", "hello world"),
    ("\t hello \n world \r", "hello world"), ("  ", None), ("", None), (None, None), ("single", "single")
])
def test_clean_text(text_input, expected_output):
    assert clean_text(text_input) == expected_output

@pytest.mark.parametrize("email_input, expected_output", [
    (" test@example.com ", "test@example.com"), ("TEST@EXAMPLE.COM", "test@example.com"),
    ("invalid-email", None), ("test@example", None), ("test@.com", None), (None, None),
    ("user.name+tag@example.com", "user.name+tag@example.com"), ("", None)
])
def test_normalize_email(email_input, expected_output):
    assert normalize_email(email_input) == expected_output

@pytest.mark.parametrize("text_input, expected_emails", [
    ("Contact us at info@example.com or sales@example.com.", ["info@example.com", "sales@example.com"]),
    ("No emails here.", []),
    ("My email is Test@Example.Co.Uk and another is USER@DOMAIN.INFO.", ["test@example.co.uk", "user@domain.info"]),
    ("Invalid: test@domain incomplete@ test@.com", []), (None, []),
    ("Email: foo@bar.com, then bar@foo.com.", ["bar@foo.com", "foo@bar.com"])
])
def test_extract_emails_from_text(text_input, expected_emails):
    assert extract_emails_from_text(text_input) == expected_emails

@pytest.mark.parametrize("url_input, include_subdomain, expected_domain", [
    ("http://www.example.com/path", False, "example.com"),
    ("https://sub.example.co.uk/path?query=1", False, "example.co.uk"),
    ("ftp://example.com", False, "example.com"),
    ("www.example.com", False, "example.com"), 
    ("example.com", False, "example.com"),     
    ("http://localhost:8000", False, "localhost"), 
    ("http://127.0.0.1/test", False, "127.0.0.1"), 
    (None, False, None), ("", False, None),
    ("http://www.example.com/path", True, "www.example.com"),
    ("https://sub.example.com", True, "sub.example.com"),
    ("https://another.sub.example.co.uk", True, "another.sub.example.co.uk"),
    ("https://another.sub.example.co.uk", False, "example.co.uk"),
    ("mailto:test@example.com", False, None), 
    ("tel:1234567890", False, None),         
    ("justaword", False, None), 
    ("word.word", False, None) 
])
def test_extract_domain(url_input, include_subdomain, expected_domain):
    assert extract_domain(url_input, include_subdomain) == expected_domain

@pytest.mark.parametrize("base_url, relative_url, expected_absolute_url", [
    ("http://www.example.com/path/", "page.html", "http://www.example.com/path/page.html"),
    ("http://www.example.com/path", "page.html", "http://www.example.com/page.html"),
    ("http://www.example.com", "/abs/page.html", "http://www.example.com/abs/page.html"),
    ("http://www.example.com", "http://othersite.com/page", "http://othersite.com/page"),
    ("http://www.example.com", None, None),
    ("http://www.example.com/path/", "  ", "http://www.example.com/path/"), 
    ("http://www.example.com/path", "  ", "http://www.example.com/path"), 
    ("http://www.example.com", "  ", "http://www.example.com"), 
    ("http://www.example.com", "  page.html  ", "http://www.example.com/page.html"),
])
def test_make_absolute_url(base_url, relative_url, expected_absolute_url):
    assert make_absolute_url(base_url, relative_url) == expected_absolute_url

# --- Tests for DomainRateLimiter ---
@pytest.mark.asyncio
async def test_domain_rate_limiter_delays_requests(monkeypatch, test_logger_instance):
    logger, temp_log_file, _ = test_logger_instance
    
    # Monkeypatch global settings that DomainRateLimiter will use
    monkeypatch.setattr(global_app_settings.crawler, 'MIN_DELAY_PER_DOMAIN_SECONDS', 0.1)
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_DELAY_PER_DOMAIN_SECONDS', 0.2)
    # MAX_CONCURRENT_REQUESTS_PER_DOMAIN is on global_app_settings itself
    monkeypatch.setattr(global_app_settings, 'MAX_CONCURRENT_REQUESTS_PER_DOMAIN', 1)


    # Use the global domain_rate_limiter instance or create a new one for testing
    # If using global, ensure its state is clean or predictable for each test.
    # Creating a new instance is safer for test isolation.
    limiter = DomainRateLimiter() 
    domain = "testdomain-delay.com" 
    
    start_time = asyncio.get_event_loop().time()
    async with await limiter.wait_for_domain(domain): 
        logger.info(f"First access to {domain}")
    first_request_end_time = asyncio.get_event_loop().time()
    
    async with await limiter.wait_for_domain(domain): 
        logger.info(f"Second access to {domain}")
    second_request_end_time = asyncio.get_event_loop().time()

    duration_first_pass = first_request_end_time - start_time
    duration_second_pass_wait = second_request_end_time - first_request_end_time
    
    logger.info(f"Duration first pass for {domain}: {duration_first_pass}, Second pass wait: {duration_second_pass_wait}")
    logger.complete()
    
    # Access the monkeypatched values for assertion
    min_delay_for_assert = global_app_settings.crawler.MIN_DELAY_PER_DOMAIN_SECONDS
    assert duration_second_pass_wait >= min_delay_for_assert * 0.8 
    
    with open(temp_log_file, "r") as f:
        log_content = f.read()
    assert f"Rate limiting domain '{domain}'" in log_content # This log should now appear

@pytest.mark.asyncio
async def test_domain_rate_limiter_concurrency(monkeypatch, test_logger_instance):
    logger, temp_log_file, _ = test_logger_instance

    # Monkeypatch global settings
    monkeypatch.setattr(global_app_settings.crawler, 'MIN_DELAY_PER_DOMAIN_SECONDS', 0.01) # Small delay
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_DELAY_PER_DOMAIN_SECONDS', 0.02) # Small delay
    monkeypatch.setattr(global_app_settings, 'MAX_CONCURRENT_REQUESTS_PER_DOMAIN', 1) # Test with 1

    limiter = DomainRateLimiter()
    domain = "concurrenttest-sem.com" 
    
    active_workers = 0
    max_active_workers = 0
    worker_lock = asyncio.Lock()

    async def worker(id_num): 
        nonlocal active_workers, max_active_workers
        async with await limiter.wait_for_domain(domain): 
            async with worker_lock:
                active_workers += 1
                max_active_workers = max(max_active_workers, active_workers)
            logger.info(f"Worker {id_num} acquired permit for {domain}, active: {active_workers}")
            await asyncio.sleep(0.1) 
            async with worker_lock:
                active_workers -= 1
            logger.info(f"Worker {id_num} releasing permit for {domain}, active: {active_workers}")

    tasks = [asyncio.create_task(worker(i)) for i in range(3)]
    await asyncio.gather(*tasks)
    
    assert max_active_workers == global_app_settings.MAX_CONCURRENT_REQUESTS_PER_DOMAIN
    logger.complete()

```

### 5.5. `lead_gen_pipeline/crawler.py`
```python
# lead_gen_pipeline/crawler.py
# Version: 2025-05-23 16:55 EDT
import httpx
import asyncio
import random
from typing import Optional, Tuple, Dict, Any, cast
from urllib.parse import urlparse, urlunparse, urljoin
import urllib.robotparser
from collections import OrderedDict # For LRU cache

# Playwright imports
from playwright.async_api import (
    async_playwright,
    Browser,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    Error as PlaywrightBaseError,
    Response as PlaywrightResponse
)

try:
    from .config import settings as global_app_settings
    from .utils import logger, async_retry, domain_rate_limiter, extract_domain, clean_text
except ImportError:
    from lead_gen_pipeline.config import settings as global_app_settings # type: ignore
    from lead_gen_pipeline.utils import logger, async_retry, domain_rate_limiter, extract_domain, clean_text # type: ignore

# Custom exception for robots.txt disallow
class RobotsTxtDisallowedError(Exception):
    """Raised when a URL is disallowed by robots.txt."""
    def __init__(self, url: str, user_agent: str):
        self.url = url
        self.user_agent = user_agent
        super().__init__(f"URL '{url}' is disallowed for user-agent '{user_agent}' by robots.txt.")

class AsyncWebCrawler:
    _playwright_instance = None
    _browser: Optional[Browser] = None
    logger_class = logger

    def __init__(self):
        self.settings = global_app_settings.crawler
        self.app_settings = global_app_settings
        self.logger = logger
        self.domain_rate_limiter = domain_rate_limiter
        self._robots_parsers_cache: OrderedDict[str, urllib.robotparser.RobotFileParser] = OrderedDict()
        self._robots_fetch_locks: Dict[str, asyncio.Lock] = {}

    def _get_random_user_agent(self) -> str:
        if self.settings.USER_AGENTS:
            return random.choice(self.settings.USER_AGENTS)
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def _construct_headers(self, url: str) -> Dict[str, str]:
        headers = {
            "User-Agent": self._get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "DNT": "1",
        }
        parsed_url = urlparse(url)
        if parsed_url.netloc:
            headers["Referer"] = "https://www.google.com/"
        return headers

    async def _fetch_and_parse_robots_txt(self, domain: str) -> Optional[urllib.robotparser.RobotFileParser]:
        robots_url_https = f"https://{domain}/robots.txt"
        robots_url_http = f"http://{domain}/robots.txt"
        robots_content: Optional[str] = None
        final_robots_url_tried = robots_url_https
        robots_fetch_headers = {"User-Agent": self._get_random_user_agent()}

        async with httpx.AsyncClient(timeout=self.settings.ROBOTS_TXT_FETCH_TIMEOUT_SECONDS, follow_redirects=True) as client:
            try:
                self.logger.debug(f"Attempting to fetch robots.txt from: {robots_url_https}")
                response = await client.get(robots_url_https, headers=robots_fetch_headers)
                final_robots_url_tried = str(response.url)
                if response.status_code == 200:
                    robots_content = response.text
                elif response.status_code == 404:
                    self.logger.debug(f"robots.txt not found at {robots_url_https} (404).")
                else:
                    self.logger.warning(f"Failed to fetch robots.txt from {robots_url_https} with status {response.status_code}. Trying HTTP.")
                    final_robots_url_tried = robots_url_http
                    response = await client.get(robots_url_http, headers=robots_fetch_headers)
                    final_robots_url_tried = str(response.url)
                    if response.status_code == 200:
                        robots_content = response.text
                    else:
                        self.logger.warning(f"Failed to fetch robots.txt from {robots_url_http} as well (status: {response.status_code}). Assuming permissive.")
                        return None
            except httpx.RequestError as e:
                self.logger.warning(f"Error fetching robots.txt from {final_robots_url_tried}: {type(e).__name__}. Assuming permissive. Error: {e}")
                return None

        if robots_content:
            parser = urllib.robotparser.RobotFileParser()
            try:
                parser.parse(robots_content.splitlines())
                self.logger.info(f"Successfully fetched and parsed robots.txt for domain: {domain} from {final_robots_url_tried}")
                return parser
            except Exception as e:
                self.logger.error(f"Error parsing robots.txt content for {domain}: {e}. Assuming permissive.")
                return None
        
        self.logger.debug(f"No robots.txt content found or fetched for {domain}. Assuming permissive.")
        return None

    async def _get_robots_parser(self, domain: str) -> Optional[urllib.robotparser.RobotFileParser]:
        if domain in self._robots_parsers_cache:
            self._robots_parsers_cache.move_to_end(domain)
            self.logger.trace(f"Using cached robots.txt parser for domain: {domain}")
            return self._robots_parsers_cache[domain]

        if domain not in self._robots_fetch_locks:
            self._robots_fetch_locks[domain] = asyncio.Lock()
        
        async with self._robots_fetch_locks[domain]:
            if domain in self._robots_parsers_cache:
                self._robots_parsers_cache.move_to_end(domain)
                return self._robots_parsers_cache[domain]

            parser = await self._fetch_and_parse_robots_txt(domain)
            
            if len(self._robots_parsers_cache) >= self.settings.ROBOTS_TXT_CACHE_SIZE:
                oldest_domain, _ = self._robots_parsers_cache.popitem(last=False)
                self.logger.debug(f"Robots.txt cache full. Removed parser for domain: {oldest_domain}")
            
            self._robots_parsers_cache[domain] = cast(urllib.robotparser.RobotFileParser, parser)
            self.logger.debug(f"Cached robots.txt parser (or None) for domain: {domain}. Cache size: {len(self._robots_parsers_cache)}")
            return parser

    async def _check_robots_txt(self, url: str) -> None:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        if not domain:
            self.logger.warning(f"Could not extract domain from URL '{url}' for robots.txt check.")
            return

        user_agent_for_robots = self.settings.ROBOTS_TXT_USER_AGENT
        self.logger.debug(f"Checking robots.txt for URL: {url} with UA: {user_agent_for_robots}")

        parser = await self._get_robots_parser(domain)

        if parser:
            is_allowed: bool
            try:
                # This call to can_fetch itself should not raise RobotsTxtDisallowedError
                is_allowed = parser.can_fetch(user_agent_for_robots, url)
            except Exception as e: # Catch any unexpected error from can_fetch() itself
                self.logger.error(f"Unexpected error during robots.txt parser.can_fetch() for {url} with UA {user_agent_for_robots}: {e}. Assuming permissive.")
                return # Assume permissive on unexpected parser error

            if not is_allowed:
                self.logger.warning(f"URL '{url}' is disallowed by robots.txt for user-agent '{user_agent_for_robots}'.")
                raise RobotsTxtDisallowedError(url, user_agent_for_robots) # This is the intended exception
            else:
                self.logger.debug(f"URL '{url}' is allowed by robots.txt for user-agent '{user_agent_for_robots}'.")
        else:
            self.logger.debug(f"No valid robots.txt parser for domain '{domain}'. Assuming permissive for URL: {url}")

    @classmethod
    async def _ensure_playwright_browser(cls) -> Browser:
        if cls._playwright_instance is None:
            cls.logger_class.info("Starting Playwright instance...")
            cls._playwright_instance = await async_playwright().start()
            cls.logger_class.info("Playwright instance started.")

        if cls._browser is None or not cls._browser.is_connected():
            cls.logger_class.info("Launching new Playwright browser (Chromium)...")
            browser_launch_options: Dict[str, Any] = {
                "headless": global_app_settings.crawler.PLAYWRIGHT_HEADLESS_MODE,
                "args": [
                    '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled', '--disable-infobars',
                    '--disable-popup-blocking', '--disable-notifications',
                    '--ignore-certificate-errors',
                ]
            }
            proxy_to_use = None
            if global_app_settings.crawler.HTTP_PROXY_URL:
                parsed_proxy = urlparse(str(global_app_settings.crawler.HTTP_PROXY_URL))
                proxy_server_url = f"{parsed_proxy.scheme}://{parsed_proxy.hostname}:{parsed_proxy.port}"
                proxy_to_use = {"server": proxy_server_url}
                if parsed_proxy.username: proxy_to_use["username"] = parsed_proxy.username
                if parsed_proxy.password: proxy_to_use["password"] = parsed_proxy.password
                cls.logger_class.info(f"Playwright will use proxy: {proxy_server_url} (auth redacted if present)")
            
            if proxy_to_use:
                browser_launch_options["proxy"] = proxy_to_use

            cls._browser = await cls._playwright_instance.chromium.launch(**browser_launch_options)
            cls.logger_class.info("Playwright browser (Chromium) launched.")
        return cls._browser

    async def _get_playwright_page(self) -> Tuple[Page, Any]:
        browser = await self._ensure_playwright_browser()
        viewport_width = random.randint(1280, 1920)
        viewport_height = random.randint(720, 1080)
        context = await browser.new_context(
            user_agent=self._get_random_user_agent(),
            viewport={"width": viewport_width, "height": viewport_height},
            java_script_enabled=True, bypass_csp=True,
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await context.new_page()
        self.logger.debug(f"New Playwright page created with UA: {await page.evaluate('navigator.userAgent')}, Viewport: {viewport_width}x{viewport_height}")
        return page, context

    @classmethod
    async def close_playwright_resources(cls):
        if cls._browser and cls._browser.is_connected():
            cls.logger_class.info("Closing Playwright browser...")
            await cls._browser.close()
            cls._browser = None
            cls.logger_class.info("Playwright browser closed.")
        if cls._playwright_instance:
            cls.logger_class.info("Stopping Playwright instance...")
            await cls._playwright_instance.stop()
            cls._playwright_instance = None
            cls.logger_class.info("Playwright instance stopped.")

    async def _fetch_with_playwright(self, url: str, timeout_ms: int) -> Tuple[str, int, str]:
        self.logger.debug(f"Attempting Playwright fetch for: {url} with timeout {timeout_ms}ms")
        page: Optional[Page] = None
        context: Optional[Any] = None 
        html_content: str = ""
        status_code: int = 0 
        final_url: str = url

        try:
            page, context = await self._get_playwright_page()
            response: Optional[PlaywrightResponse] = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=timeout_ms
            )
            if response:
                status_code = response.status
                html_content = await page.content()
                final_url = page.url
                if 200 <= status_code < 300:
                    self.logger.success(f"Successfully fetched (Playwright) {final_url} with status {status_code}")
                else:
                    self.logger.warning(f"Fetched (Playwright) {final_url} with status {status_code}")
            else:
                self.logger.error(f"Playwright navigation to {url} returned no response object.")
                status_code = 599 
                raise PlaywrightBaseError(f"Playwright navigation to {url} failed to return a response object.")
        except PlaywrightTimeoutError as e:
            self.logger.error(f"Playwright TimeoutError for {url} after {timeout_ms}ms: {str(e)[:200]}")
            raise 
        except PlaywrightBaseError as e: 
            self.logger.error(f"PlaywrightBaseError for {url}: {type(e).__name__} - {str(e)[:200]}")
            raise 
        except Exception as e: 
            self.logger.error(f"Unexpected error during Playwright fetch for {url}: {type(e).__name__} - {str(e)[:200]}")
            status_code = 597 
            raise PlaywrightBaseError(f"Unexpected error in Playwright operation for {url}: {e}") from e
        finally:
            if context:
                try:
                    await context.close()
                    self.logger.debug(f"Playwright context for {url} closed.")
                except Exception as e:
                    self.logger.error(f"Error closing Playwright context for {url}: {e}")
        return html_content, status_code, final_url

    async def _perform_httpx_fetch_attempt(
        self, url: str, headers: Dict[str, str], proxies: Optional[Dict[str, str]] = None
    ) -> Tuple[str, int, str]:
        client_kwargs: Dict[str, Any] = {
            "headers": headers, "timeout": self.settings.DEFAULT_TIMEOUT_SECONDS,
            "follow_redirects": True, "verify": True
        }
        if proxies: client_kwargs["proxies"] = proxies
        async with httpx.AsyncClient(**client_kwargs) as client:
            self.logger.info(f"Attempting HTTPX fetch for: {url}")
            response = await client.get(url)
            final_url = str(response.url)
            status_code = response.status_code
            response.raise_for_status() 
            html_content = response.text
            self.logger.success(f"Successfully fetched (HTTPX) {final_url} with status {status_code}")
            return html_content, status_code, final_url

    @async_retry(exceptions=(httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError, PlaywrightBaseError, RobotsTxtDisallowedError, RuntimeError))
    async def fetch_page_content(
        self, url: str, use_playwright: bool
    ) -> Tuple[str, int, str]:
        
        if self.settings.RESPECT_ROBOTS_TXT:
            await self._check_robots_txt(url) 

        headers = self._construct_headers(url)
        proxies_dict: Optional[Dict[str, str]] = None
        if self.settings.HTTP_PROXY_URL:
            proxies_dict = {
                "http://": str(self.settings.HTTP_PROXY_URL),
                "https": str(self.settings.HTTPS_PROXY_URL) if self.settings.HTTPS_PROXY_URL else str(self.settings.HTTP_PROXY_URL)
            }
        
        html_content: str = ""
        status_code: int = 0
        final_url: str = url

        async with await self.domain_rate_limiter.wait_for_domain(extract_domain(url)):
            if use_playwright:
                self.logger.info(f"Fetching (Playwright) for {url}")
                playwright_timeout_ms = self.settings.DEFAULT_TIMEOUT_SECONDS * 1000 * 2
                html_content, status_code, final_url = await self._fetch_with_playwright(url, timeout_ms=playwright_timeout_ms)
            else: 
                html_content, status_code, final_url = await self._perform_httpx_fetch_attempt(url, headers, proxies_dict)
        
        if html_content:
            cleaned_text_for_captcha_check = clean_text(html_content[:2000].lower())
            if cleaned_text_for_captcha_check and any(
                keyword in cleaned_text_for_captcha_check for keyword in ["captcha", "are you a robot", "verify you're human", "recaptcha"]
            ):
                self.logger.warning(f"Potential CAPTCHA detected on {final_url}. Content might be a challenge page.")
        
        return html_content, status_code, final_url

    async def fetch_page(
        self, url: str, use_playwright: Optional[bool] = None
    ) -> Tuple[Optional[str], int, str]:
        domain = extract_domain(url)
        if not domain:
            self.logger.error(f"Invalid URL or could not extract domain: {url}")
            return None, 0, url 

        should_use_playwright = use_playwright if use_playwright is not None else self.settings.USE_PLAYWRIGHT_BY_DEFAULT
        
        try:
            html_content, status_code, final_url = await self.fetch_page_content(url, should_use_playwright)
            return html_content, status_code, final_url
        except RobotsTxtDisallowedError as e:
            self.logger.error(f"FETCH_PAGE_FINAL: RobotsTxtDisallowedError for {e.url} with UA '{e.user_agent}'. Not fetched.")
            return None, 403, e.url 
        except httpx.HTTPStatusError as e:
            self.logger.error(f"FETCH_PAGE_FINAL: HTTPStatusError for {url} (final: {str(e.request.url)}): Status {e.response.status_code}")
            return None, e.response.status_code, str(e.request.url)
        except httpx.TimeoutException as e:
            self.logger.error(f"FETCH_PAGE_FINAL: TimeoutException for {url}: {e}")
            return None, 408, url 
        except httpx.RequestError as e: 
            self.logger.error(f"FETCH_PAGE_FINAL: RequestError for {url}: {type(e).__name__} - {e}")
            final_exc_url = str(e.request.url) if hasattr(e, 'request') and e.request else url
            return None, 599, final_exc_url 
        except PlaywrightBaseError as e: 
            self.logger.error(f"FETCH_PAGE_FINAL: PlaywrightBaseError for {url}: {type(e).__name__} - {str(e)[:200]}")
            return None, 598, url 
        except RuntimeError as e: 
            self.logger.opt(exception=True).critical(f"FETCH_PAGE_FINAL: Unexpected RuntimeError for {url}: {e}")
            return None, 500, url
        except Exception as e:
            self.logger.opt(exception=True).critical(f"FETCH_PAGE_FINAL: Truly unexpected error for {url}: {e}")
            return None, 500, url

    async def close(self):
        self.logger.info("AsyncWebCrawler close() called.")
        await self.close_playwright_resources()
        self._robots_parsers_cache.clear()
        self._robots_fetch_locks.clear()
        self.logger.info("Robots.txt cache and fetch locks cleared.")


```

### 5.6. `tests/unit/test_crawler.py`
```python
# tests/unit/test_crawler.py
# Version: 2025-05-23 17:00 EDT
import pytest
import httpx
import respx # Import respx directly
import asyncio
from pathlib import Path
import sys
import urllib.robotparser
import re # Import re for escaping
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock, call
from collections import OrderedDict

PROJECT_ROOT_FOR_IMPORTS = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORTS))

from lead_gen_pipeline.crawler import AsyncWebCrawler, RobotsTxtDisallowedError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightBaseError
from lead_gen_pipeline.config import settings as global_app_settings, AppSettings, CrawlerSettings, LoggingSettings
from lead_gen_pipeline.utils import logger as utils_logger, setup_logger

# --- Fixtures ---
@pytest.fixture
def crawler_instance(event_loop) -> AsyncWebCrawler:
    instance = AsyncWebCrawler()
    AsyncWebCrawler._playwright_instance = None
    AsyncWebCrawler._browser = None
    return instance

@pytest.fixture(scope="function")
def test_logger_instance_for_crawler(tmp_path):
    original_logging_settings = global_app_settings.logging
    temp_log_file = tmp_path / "crawler_test_app.log"
    temp_error_log_file = tmp_path / "crawler_test_error.log"
    test_logging_settings = LoggingSettings(
        LOG_LEVEL="DEBUG",
        LOG_FILE_PATH=temp_log_file,
        ERROR_LOG_FILE_PATH=temp_error_log_file,
    )
    configured_logger = setup_logger(custom_logging_settings=test_logging_settings)
    yield configured_logger, temp_log_file, temp_error_log_file
    setup_logger(custom_logging_settings=original_logging_settings)


@pytest.fixture
def mock_playwright_page_context():
    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_response = AsyncMock()

    mock_page.goto = AsyncMock(return_value=mock_response)
    mock_page.content = AsyncMock(return_value="<html><body>Playwright Content</body></html>")
    type(mock_page).url = PropertyMock(return_value="http://playwright.final.url/MOCK")

    type(mock_response).status = PropertyMock(return_value=200)
    mock_response.ok = PropertyMock(return_value=True)
    
    mock_context.close = AsyncMock()
    mock_page.close = AsyncMock()

    return mock_page, mock_context, mock_response

# --- Robots.txt Test Data ---
ROBOTS_TXT_ALLOW_ALL = """
User-agent: *
Disallow:
"""

ROBOTS_TXT_DISALLOW_PATH = """
User-agent: *
Disallow: /private/
Disallow: /confidential.html

User-agent: MySpecificBot
Disallow: /mybot-only-private/
"""

ROBOTS_TXT_EMPTY = ""


# --- Tests for HTTPX Fetching (Largely Unchanged) ---
@respx.mock # Decorator is used, no need to inject respx_router
@pytest.mark.asyncio
async def test_fetch_page_httpx_success(crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    url = "http://testsuccess.com"
    expected_html = "<html><body>Success!</body></html>"
    expected_status = 200
    # Use the imported respx object directly
    route = respx.get(url).mock(return_value=httpx.Response(expected_status, html=expected_html))
    html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=False)
    assert status == expected_status
    assert html == expected_html
    assert final_url == url
    assert route.call_count == 1

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_httpx_redirect(crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    initial_url = "http://redirectme.com"
    final_url_target = "http://finaldestination.com"
    expected_html = "<html><body>Redirected Content</body></html>"
    route1 = respx.get(initial_url).mock(return_value=httpx.Response(301, headers={"Location": final_url_target}))
    route2 = respx.get(final_url_target).mock(return_value=httpx.Response(200, html=expected_html))
    html, status, final_url_returned = await crawler_instance.fetch_page(initial_url, use_playwright=False)
    assert status == 200
    assert html == expected_html
    assert final_url_returned == final_url_target

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_httpx_404_error_no_retry(crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_RETRIES', 0)
    url = "http://notfound.com"
    respx.get(url).mock(return_value=httpx.Response(404))
    html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=False)
    assert status == 404
    assert html is None

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_httpx_500_error_no_retry(crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_RETRIES', 0)
    url = "http://servererror.com"
    respx.get(url).mock(return_value=httpx.Response(500))
    html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=False)
    assert status == 500
    assert html is None

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_httpx_timeout_no_retry(crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_RETRIES', 0)
    monkeypatch.setattr(crawler_instance.settings, 'DEFAULT_TIMEOUT_SECONDS', 0.1)
    url = "http://timeoutsite.com"
    request = httpx.Request("GET", url)
    respx.get(url).mock(side_effect=httpx.TimeoutException("Test timeout", request=request))
    html, status, final_url_returned = await crawler_instance.fetch_page(url, use_playwright=False)
    assert status == 408
    assert html is None

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_httpx_network_error_no_retry(crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_RETRIES', 0)
    url = "http://networkerror.com"
    request = httpx.Request("GET", url)
    respx.get(url).mock(side_effect=httpx.ConnectError("Test connection error", request=request))
    html, status, final_url_returned = await crawler_instance.fetch_page(url, use_playwright=False)
    assert status == 599
    assert html is None

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_uses_retry_decorator_successfully_httpx(crawler_instance: AsyncWebCrawler, monkeypatch, test_logger_instance_for_crawler):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    logger, temp_log_file, _ = test_logger_instance_for_crawler
    url = "http://retrytest-httpx.com"
    expected_html = "<html><body>Retry Success!</body></html>"
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_RETRIES', 1)
    mock_responses = [ httpx.Response(500), httpx.Response(200, html=expected_html) ]
    respx.get(url).mock(side_effect=mock_responses)
    with patch('lead_gen_pipeline.utils.asyncio.sleep', AsyncMock()):
        html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=False)
    assert status == 200
    assert html == expected_html

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_exhausts_retries_httpx(crawler_instance: AsyncWebCrawler, monkeypatch, test_logger_instance_for_crawler):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    logger, temp_log_file, temp_error_log_file = test_logger_instance_for_crawler
    url = "http://alwaysfail-httpx.com"
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_RETRIES', 1)
    respx.get(url).mock(return_value=httpx.Response(500))
    with patch('lead_gen_pipeline.utils.asyncio.sleep', AsyncMock()):
        html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=False)
    assert status == 500
    assert html is None


# --- Tests for Playwright Fetching (`_fetch_with_playwright`) ---
@pytest.mark.asyncio
@patch.object(AsyncWebCrawler, '_get_playwright_page', new_callable=AsyncMock)
async def test_fetch_with_playwright_success(mock_get_page, crawler_instance: AsyncWebCrawler, mock_playwright_page_context):
    mock_page, mock_context, mock_response = mock_playwright_page_context
    mock_get_page.return_value = (mock_page, mock_context)
    
    url = "http://playwrightsuccess.com"
    timeout_ms = 30000
    expected_html = "<html><body>Playwright Content</body></html>"
    expected_status = 200
    expected_final_url = "http://playwright.final.url/MOCK"

    type(mock_page).url = PropertyMock(return_value=expected_final_url)
    mock_page.content = AsyncMock(return_value=expected_html)
    type(mock_response).status = PropertyMock(return_value=expected_status)
    mock_page.goto.return_value = mock_response

    html, status, final_url = await crawler_instance._fetch_with_playwright(url, timeout_ms)

    assert html == expected_html
    assert status == expected_status
    assert final_url == expected_final_url

@pytest.mark.asyncio
@patch.object(AsyncWebCrawler, '_get_playwright_page', new_callable=AsyncMock)
async def test_fetch_with_playwright_timeout_error(mock_get_page, crawler_instance: AsyncWebCrawler, mock_playwright_page_context):
    mock_page, mock_context, _ = mock_playwright_page_context
    mock_get_page.return_value = (mock_page, mock_context)
    url = "http://playwrighttimeout.com"
    timeout_ms = 100 
    mock_page.goto.side_effect = PlaywrightTimeoutError("Test Playwright Timeout")
    with pytest.raises(PlaywrightTimeoutError, match="Test Playwright Timeout"):
        await crawler_instance._fetch_with_playwright(url, timeout_ms)
    mock_context.close.assert_awaited_once()

@pytest.mark.asyncio
@patch.object(AsyncWebCrawler, '_get_playwright_page', new_callable=AsyncMock)
async def test_fetch_with_playwright_base_error(mock_get_page, crawler_instance: AsyncWebCrawler, mock_playwright_page_context):
    mock_page, mock_context, _ = mock_playwright_page_context
    mock_get_page.return_value = (mock_page, mock_context)
    url = "http://playwrightbaseerror.com"
    timeout_ms = 30000
    mock_page.goto.side_effect = PlaywrightBaseError("Test Playwright Base Error")
    with pytest.raises(PlaywrightBaseError, match="Test Playwright Base Error"):
        await crawler_instance._fetch_with_playwright(url, timeout_ms)
    mock_context.close.assert_awaited_once()

@pytest.mark.asyncio
@patch.object(AsyncWebCrawler, '_get_playwright_page', new_callable=AsyncMock)
async def test_fetch_with_playwright_no_response_object(mock_get_page, crawler_instance: AsyncWebCrawler, mock_playwright_page_context):
    mock_page, mock_context, _ = mock_playwright_page_context
    mock_get_page.return_value = (mock_page, mock_context)
    mock_page.goto.return_value = None 
    url = "http://playwrightnoresponse.com"
    timeout_ms = 30000
    with pytest.raises(PlaywrightBaseError, match=f"Playwright navigation to {url} failed to return a response object."):
        await crawler_instance._fetch_with_playwright(url, timeout_ms)
    mock_context.close.assert_awaited_once()

# --- Tests for `fetch_page` using Playwright ---
@pytest.mark.asyncio
@patch('lead_gen_pipeline.crawler.AsyncWebCrawler._fetch_with_playwright', new_callable=AsyncMock)
async def test_fetch_page_uses_playwright_successfully(mock_internal_fetch_pw, crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    url = "http://useplaywright.com"
    expected_html = "<html>Playwright success</html>"
    expected_status = 200
    expected_final_url = "http://useplaywright.final.com"
    mock_internal_fetch_pw.return_value = (expected_html, expected_status, expected_final_url)
    monkeypatch.setattr(global_app_settings.crawler, 'USE_PLAYWRIGHT_BY_DEFAULT', True)

    with patch('lead_gen_pipeline.utils.domain_rate_limiter.wait_for_domain', AsyncMock()) as mock_rate_limiter:
        class DummyAsyncContextManager:
            async def __aenter__(self): return self
            async def __aexit__(self, exc_type, exc_val, exc_tb): pass
        mock_rate_limiter.return_value = DummyAsyncContextManager()
        html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=True)
    assert html == expected_html
    assert status == expected_status

@pytest.mark.asyncio
@patch('lead_gen_pipeline.crawler.AsyncWebCrawler._fetch_with_playwright', new_callable=AsyncMock)
async def test_fetch_page_playwright_retry_and_fail(mock_internal_fetch_pw, crawler_instance: AsyncWebCrawler, monkeypatch, test_logger_instance_for_crawler):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    logger, temp_log_file, temp_error_log_file = test_logger_instance_for_crawler
    url = "http://playwrightretryfail.com"
    monkeypatch.setattr(global_app_settings.crawler, 'MAX_RETRIES', 1)
    mock_internal_fetch_pw.side_effect = PlaywrightTimeoutError("PW Timeout for retry test")

    with patch('lead_gen_pipeline.utils.asyncio.sleep', AsyncMock()):
        with patch('lead_gen_pipeline.utils.domain_rate_limiter.wait_for_domain', AsyncMock()) as mock_rate_limiter:
            class DummyAsyncContextManager:
                async def __aenter__(self): return self
                async def __aexit__(self, exc_type, exc_val, exc_tb): pass
            mock_rate_limiter.return_value = DummyAsyncContextManager()
            html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=True)
    assert html is None
    assert status == 598


# --- New Tests for Robots.txt Functionality ---

@respx.mock
@pytest.mark.asyncio
async def test_fetch_and_parse_robots_txt_success_https(crawler_instance: AsyncWebCrawler): 
    domain = "example.com"
    robots_url = f"https://{domain}/robots.txt"
    respx.get(robots_url).mock(return_value=httpx.Response(200, text=ROBOTS_TXT_ALLOW_ALL))
    
    parser = await crawler_instance._fetch_and_parse_robots_txt(domain)
    assert parser is not None
    assert isinstance(parser, urllib.robotparser.RobotFileParser)
    assert parser.can_fetch("*", f"https://{domain}/anypage.html") is True

@respx.mock
@pytest.mark.asyncio
async def test_fetch_and_parse_robots_txt_success_http_fallback(crawler_instance: AsyncWebCrawler): 
    domain = "fallback.com"
    robots_url_https = f"https://{domain}/robots.txt"
    robots_url_http = f"http://{domain}/robots.txt"
    respx.get(robots_url_https).mock(return_value=httpx.Response(500)) 
    respx.get(robots_url_http).mock(return_value=httpx.Response(200, text=ROBOTS_TXT_DISALLOW_PATH))
    
    parser = await crawler_instance._fetch_and_parse_robots_txt(domain)
    assert parser is not None
    assert parser.can_fetch("*", f"http://{domain}/allowed.html") is True
    assert parser.can_fetch("*", f"http://{domain}/private/page.html") is False

@respx.mock
@pytest.mark.asyncio
async def test_fetch_robots_txt_not_found_404(crawler_instance: AsyncWebCrawler): 
    domain = "notfoundrobots.com"
    robots_url_https = f"https://{domain}/robots.txt"
    robots_url_http = f"http://{domain}/robots.txt" 
    respx.get(robots_url_https).mock(return_value=httpx.Response(404))
    http_route = respx.get(robots_url_http) 
    
    parser = await crawler_instance._fetch_and_parse_robots_txt(domain)
    assert parser is None 
    assert http_route.call_count == 0


@respx.mock
@pytest.mark.asyncio
async def test_fetch_robots_txt_network_error(crawler_instance: AsyncWebCrawler): 
    domain = "networkerrorrobots.com"
    robots_url = f"https://{domain}/robots.txt"
    request = httpx.Request("GET", robots_url) 
    respx.get(robots_url).mock(side_effect=httpx.ConnectError("Connection failed", request=request))
    
    parser = await crawler_instance._fetch_and_parse_robots_txt(domain)
    assert parser is None

@pytest.mark.asyncio
async def test_get_robots_parser_caching(crawler_instance: AsyncWebCrawler, monkeypatch):
    domain = "cachetest.com"
    mock_parser_instance = urllib.robotparser.RobotFileParser()
    mock_parser_instance.parse(ROBOTS_TXT_ALLOW_ALL.splitlines())

    mock_fetch_parse = AsyncMock(return_value=mock_parser_instance)
    monkeypatch.setattr(crawler_instance, '_fetch_and_parse_robots_txt', mock_fetch_parse)

    parser1 = await crawler_instance._get_robots_parser(domain)
    assert parser1 == mock_parser_instance
    mock_fetch_parse.assert_awaited_once_with(domain)
    assert domain in crawler_instance._robots_parsers_cache

    parser2 = await crawler_instance._get_robots_parser(domain)
    assert parser2 == mock_parser_instance
    mock_fetch_parse.assert_awaited_once() 

    monkeypatch.setattr(crawler_instance.settings, 'ROBOTS_TXT_CACHE_SIZE', 1)
    await crawler_instance._get_robots_parser("anotherdomain.com") 
    assert domain not in crawler_instance._robots_parsers_cache 
    assert "anotherdomain.com" in crawler_instance._robots_parsers_cache
    assert mock_fetch_parse.call_count == 2


@pytest.mark.asyncio
async def test_check_robots_txt_allowed(crawler_instance: AsyncWebCrawler, monkeypatch):
    url = "http://alloweddomain.com/allowed/path"
    domain = "alloweddomain.com"
    mock_parser = MagicMock(spec=urllib.robotparser.RobotFileParser)
    mock_parser.can_fetch.return_value = True
    
    monkeypatch.setattr(crawler_instance, '_get_robots_parser', AsyncMock(return_value=mock_parser))
    
    await crawler_instance._check_robots_txt(url) 
    crawler_instance._get_robots_parser.assert_awaited_once_with(domain)
    mock_parser.can_fetch.assert_called_once_with(crawler_instance.settings.ROBOTS_TXT_USER_AGENT, url)

@pytest.mark.asyncio
async def test_check_robots_txt_disallowed(crawler_instance: AsyncWebCrawler, monkeypatch):
    url = "http://disalloweddomain.com/forbidden/path"
    domain = "disalloweddomain.com"
    user_agent = crawler_instance.settings.ROBOTS_TXT_USER_AGENT # Should be '*' by default
    
    mock_parser = MagicMock(spec=urllib.robotparser.RobotFileParser)
    mock_parser.can_fetch.return_value = False # Simulate disallowed
    
    monkeypatch.setattr(crawler_instance, '_get_robots_parser', AsyncMock(return_value=mock_parser))
    
    expected_message = f"URL '{url}' is disallowed for user-agent '{user_agent}' by robots.txt."
    with pytest.raises(RobotsTxtDisallowedError, match=re.escape(expected_message)):
        await crawler_instance._check_robots_txt(url)
    crawler_instance._get_robots_parser.assert_awaited_once_with(domain)
    mock_parser.can_fetch.assert_called_once_with(user_agent, url)

@pytest.mark.asyncio
async def test_check_robots_txt_no_parser_is_permissive(crawler_instance: AsyncWebCrawler, monkeypatch):
    url = "http://noparserdomain.com/some/path"
    monkeypatch.setattr(crawler_instance, '_get_robots_parser', AsyncMock(return_value=None))
    await crawler_instance._check_robots_txt(url)

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_respects_robots_txt_disallowed(crawler_instance: AsyncWebCrawler, monkeypatch): 
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', True)
    monkeypatch.setattr(crawler_instance.settings, 'ROBOTS_TXT_USER_AGENT', 'TestAgent')
    
    domain = "robotstest.com"
    url_allowed = f"http://{domain}/allowed.html"
    url_disallowed = f"http://{domain}/disallowed.html"
    
    robots_content = "User-agent: TestAgent\nDisallow: /disallowed.html"
    respx.get(f"https://{domain}/robots.txt").mock(return_value=httpx.Response(200, text=robots_content))
    respx.get(f"http://{domain}/robots.txt").mock(return_value=httpx.Response(404))

    respx.get(url_allowed).mock(return_value=httpx.Response(200, html="Allowed page"))
    disallowed_route = respx.get(url_disallowed) 

    html, status, _ = await crawler_instance.fetch_page(url_allowed, use_playwright=False)
    assert status == 200
    assert html == "Allowed page"

    html, status, final_url = await crawler_instance.fetch_page(url_disallowed, use_playwright=False)
    assert html is None
    assert status == 403 
    assert final_url == url_disallowed
    assert disallowed_route.call_count == 0

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_respect_robots_txt_off(crawler_instance: AsyncWebCrawler, monkeypatch): 
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False) 
    
    domain = "robotsoff.com"
    url_disallowed_by_rules = f"http://{domain}/disallowed.html"
        
    page_route = respx.get(url_disallowed_by_rules).mock(return_value=httpx.Response(200, html="Fetched anyway"))

    # Patch _check_robots_txt to ensure it's not called when RESPECT_ROBOTS_TXT is False
    with patch.object(crawler_instance, '_check_robots_txt', new_callable=AsyncMock) as mock_check_robots:
        html, status, _ = await crawler_instance.fetch_page(url_disallowed_by_rules, use_playwright=False)
    
    assert status == 200
    assert html == "Fetched anyway"
    mock_check_robots.assert_not_awaited() 
    assert page_route.call_count == 1


@pytest.mark.asyncio
async def test_crawler_close_clears_robots_cache(crawler_instance: AsyncWebCrawler, monkeypatch):
    domain = "domain1.com"
    mock_parser = urllib.robotparser.RobotFileParser()
    crawler_instance._robots_parsers_cache[domain] = mock_parser
    crawler_instance._robots_fetch_locks[domain] = asyncio.Lock()
    assert domain in crawler_instance._robots_parsers_cache
    assert domain in crawler_instance._robots_fetch_locks

    monkeypatch.setattr(AsyncWebCrawler, 'close_playwright_resources', AsyncMock())

    await crawler_instance.close()
    
    assert not crawler_instance._robots_parsers_cache 
    assert not crawler_instance._robots_fetch_locks 
    AsyncWebCrawler.close_playwright_resources.assert_awaited_once()


# --- General Crawler Tests ---
@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_rate_limiter_called_httpx(crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    url = "http://ratelimited-httpx.com"
    respx.get(url).mock(return_value=httpx.Response(200, html="OK"))
    with patch('lead_gen_pipeline.utils.domain_rate_limiter.wait_for_domain', AsyncMock()) as mock_wait_for_domain:
        class DummyAsyncContextManager:
            async def __aenter__(self): return self
            async def __aexit__(self, exc_type, exc_val, exc_tb): pass
        mock_wait_for_domain.return_value = DummyAsyncContextManager()
        await crawler_instance.fetch_page(url, use_playwright=False)
    mock_wait_for_domain.assert_awaited_once_with("ratelimited-httpx.com")

@pytest.mark.asyncio
async def test_fetch_page_invalid_url_domain(crawler_instance: AsyncWebCrawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    url = "mailto:test@example.com"
    html, status, final_url = await crawler_instance.fetch_page(url)
    assert html is None
    assert status == 0

@respx.mock
@pytest.mark.asyncio
async def test_fetch_page_captcha_detection_httpx(crawler_instance: AsyncWebCrawler, test_logger_instance_for_crawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    logger, temp_log_file, _ = test_logger_instance_for_crawler
    url = "http://captchasite-httpx.com"
    captcha_html = "<html><body>Please solve this reCAPTCHA to continue.</body></html>"
    respx.get(url).mock(return_value=httpx.Response(200, html=captcha_html))
    html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=False)
    assert status == 200
    assert html == captcha_html
    logger.complete()
    with open(temp_log_file, "r") as f: log_content = f.read()
    assert "Potential CAPTCHA detected" in log_content

@pytest.mark.asyncio
@patch('lead_gen_pipeline.crawler.AsyncWebCrawler._fetch_with_playwright', new_callable=AsyncMock)
async def test_fetch_page_captcha_detection_playwright(mock_internal_fetch_pw, crawler_instance: AsyncWebCrawler, test_logger_instance_for_crawler, monkeypatch):
    monkeypatch.setattr(crawler_instance.settings, 'RESPECT_ROBOTS_TXT', False)
    logger, temp_log_file, _ = test_logger_instance_for_crawler
    url = "http://captchasite-pw.com"
    captcha_html = "<html><body>Please solve this reCAPTCHA to continue. Playwright</body></html>"
    mock_internal_fetch_pw.return_value = (captcha_html, 200, url)
    monkeypatch.setattr(global_app_settings.crawler, 'USE_PLAYWRIGHT_BY_DEFAULT', True)

    with patch('lead_gen_pipeline.utils.domain_rate_limiter.wait_for_domain', AsyncMock()) as mock_rate_limiter:
        class DummyAsyncContextManager:
            async def __aenter__(self): return self
            async def __aexit__(self, exc_type, exc_val, exc_tb): pass
        mock_rate_limiter.return_value = DummyAsyncContextManager()
        html, status, final_url = await crawler_instance.fetch_page(url, use_playwright=True)
    assert status == 200
    assert html == captcha_html
    logger.complete()
    with open(temp_log_file, "r") as f: log_content = f.read()
    assert "Potential CAPTCHA detected" in log_content

@patch.object(AsyncWebCrawler, 'close_playwright_resources', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_crawler_close_calls_playwright_close(mock_close_pw_resources, crawler_instance):
    await crawler_instance.close()
    mock_close_pw_resources.assert_awaited_once()


```

### 5.7. `lead_gen_pipeline/scraper.py`
```python
# lead_gen_pipeline/scraper.py
# Version: 2025-05-23 17:55 EDT

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

# Pre-compiled regex patterns
PHONE_REGEX_PATTERNS = [
    re.compile(r'''
        (\+\d{1,3}[-.\s]?)?        # Optional country code
        (\(?\d{3}\)?[-.\s]?)       # Area code (optional parentheses)
        (\d{3}[-.\s]?)             # First 3 digits
        (\d{4})                    # Last 4 digits
        (\s*(ext|x|ext.)\s*\d{1,5})? # Optional extension
    ''', re.VERBOSE | re.IGNORECASE)
]

# Dictionary for social media platform identification
SOCIAL_MEDIA_PLATFORMS = {
    "linkedin": "linkedin.com",
    "twitter": "twitter.com",
    "facebook": "facebook.com",
    "instagram": "instagram.com",
    "youtube": "youtube.com", # Covers youtube.com and youtu.be via redirects usually
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
                        if not potential_name.isdigit() and len(potential_name.split()) <= 4: 
                            logger.debug(f"Potential company name from title: {potential_name}")
                            return potential_name
                        else:
                            logger.debug(f"Title part '{potential_name}' deemed not suitable as company name (too long/generic after split, or numeric).")
        
        logger.info("Company name not definitively found.")
        return None

    def _normalize_phone_for_deduplication(self, phone_str: str) -> str:
        return re.sub(r'\D', '', phone_str)

    def extract_phone_numbers(self) -> List[str]:
        unique_phones_map: Dict[str, str] = {}

        # Strategy 1: tel: links
        tel_links = self.soup.select('a[href^="tel:"]')
        for link_tag in tel_links:
            href_attr = link_tag.get("href")
            if not href_attr:
                continue

            phone_from_href = clean_text(href_attr.replace("tel:", ""))
            if not phone_from_href: 
                continue

            normalized_key_href = self._normalize_phone_for_deduplication(phone_from_href)
            if not (normalized_key_href and len(normalized_key_href) >= 7):
                continue

            preferred_display_phone = phone_from_href 

            phone_text_content = self._extract_text(link_tag)
            if phone_text_content:
                # Attempt to match a phone pattern within the link's text
                cleaned_phone_text_content = clean_text(phone_text_content)
                if cleaned_phone_text_content:
                    for pattern in PHONE_REGEX_PATTERNS:
                        match_in_text = pattern.search(cleaned_phone_text_content)
                        if match_in_text:
                            matched_text_phone_part = clean_text(match_in_text.group(0))
                            normalized_key_text_part = self._normalize_phone_for_deduplication(matched_text_phone_part)
                            if normalized_key_text_part == normalized_key_href:
                                preferred_display_phone = matched_text_phone_part
                                logger.debug(f"Preferred text version for tel link: '{preferred_display_phone}' (matched by regex from text) over href raw: '{phone_from_href}'")
                                break # Found a good text representation

            if normalized_key_href not in unique_phones_map:
                logger.debug(f"Found phone via tel: link: {preferred_display_phone} (normalized: {normalized_key_href})")
                unique_phones_map[normalized_key_href] = preferred_display_phone
            else:
                logger.trace(f"Duplicate phone (from tel: {preferred_display_phone}, normalized: {normalized_key_href}) already found as {unique_phones_map[normalized_key_href]}")
        
        # Strategy 2: Regex on text content
        body_tag = self.soup.body
        if body_tag:
            page_text = self._extract_text(body_tag) 
            if page_text:
                for pattern in PHONE_REGEX_PATTERNS:
                    matches = pattern.finditer(page_text)
                    for match in matches:
                        phone_candidate = clean_text(match.group(0))
                        if phone_candidate:
                            normalized_key = self._normalize_phone_for_deduplication(phone_candidate)
                            if normalized_key and len(normalized_key) >= 7:
                                if normalized_key not in unique_phones_map:
                                    logger.debug(f"Found phone via regex: {phone_candidate} (normalized: {normalized_key})")
                                    unique_phones_map[normalized_key] = phone_candidate
                                else:
                                    logger.trace(f"Duplicate phone (from regex: {phone_candidate}, normalized: {normalized_key}) already found as {unique_phones_map[normalized_key]}")
        
        found_phones_list = sorted(list(unique_phones_map.values()))
        logger.info(f"Found {len(found_phones_list)} unique phone number(s).")
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
            body_text = self._extract_text(body_tag)
            if body_text:
                emails_from_text = extract_emails_from_text(body_text)
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

        elements_with_address_class = self.soup.select('.address, [class*="location"], [id*="address"], [id*="location"]')
        for elem in elements_with_address_class:
            if elem.get("itemtype") and "PostalAddress" in elem.get("itemtype", ""):
                continue
            address_text_lines = []
            for content_node in elem.contents:
                if isinstance(content_node, Tag):
                    if content_node.name == 'br':
                        pass 
                    else: 
                        cleaned_line = self._extract_text(content_node)
                        if cleaned_line:
                            address_text_lines.append(cleaned_line)
                else: 
                    cleaned_line = clean_text(str(content_node))
                    if cleaned_line:
                        address_text_lines.append(cleaned_line)
            
            potential_address = clean_text(" ".join(address_text_lines))
            if potential_address and len(potential_address) > 10: 
                if any(char.isdigit() for char in potential_address):
                    logger.debug(f"Potential address from class/id '.address' or similar: {potential_address}")
                    found_addresses.add(potential_address)

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
                parsed_link_netloc = urlparse(abs_href).netloc.lower().replace("www.", "")
            except Exception:
                logger.warning(f"Could not parse URL for social media link: {abs_href}")
                continue 

            for platform_key, platform_domain_pattern in SOCIAL_MEDIA_PLATFORMS.items():
                if platform_domain_pattern in parsed_link_netloc:
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
        
        extracted_summary = {k: v for k, v in self.scraped_data.items() if v or isinstance(v, list) and v}
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
                Another contact: (555) 987-6543. General inquiries: general@testco.com
            </footer>
        </body>
    </html>
    """
    test_url = "https://www.originaltestco.com/somepage"
    scraper = HTMLScraper(html_content=sample_html, source_url=test_url)
    data = scraper.scrape()
    
    import json
    print(json.dumps(data, indent=4))

    print("\n--- Testing No Info ---")
    no_info_html = """<html><head><title>Empty Page</title></head><body><p>Nothing here</p></body></html>"""
    scraper_no_info = HTMLScraper(html_content=no_info_html, source_url="http://noinfo.com")
    data_no_info = scraper_no_info.scrape()
    print(json.dumps(data_no_info, indent=4))

    print("\n--- Testing Complex Footer ---")
    complex_footer_html = """
    <html><head><title>Complex Co</title></head><body>
    <footer><a href="https://www.linkedin.com/in/complex">LinkedIn Profile</a></footer>
    </body></html>"""
    scraper_complex = HTMLScraper(html_content=complex_footer_html, source_url="http://complex.com")
    data_complex = scraper_complex.scrape()
    print(json.dumps(data_complex, indent=4))


```

### 5.8. `tests/unit/test_scraper.py`
```python
# tests/unit/test_scraper.py
# Version: 2025-05-23 17:25 EDT

import pytest
from pathlib import Path
import sys

PROJECT_ROOT_FOR_IMPORTS = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORTS))

from lead_gen_pipeline.scraper import HTMLScraper

# --- Test HTML Samples ---

SAMPLE_HTML_BASIC_CONTACT = """
<html>
    <head>
        <title>Basic Contact Page - MyCompany</title>
        <meta name="description" content="Contact MyCompany for services.">
        <meta property="og:site_name" content="MyCo Official">
        <link rel="canonical" href="https://www.mycompany.com/contact-us">
    </head>
    <body>
        <h1>Contact Us</h1>
        <p>Email us at <a href="mailto:contact@mycompany.com">contact@mycompany.com</a>.</p>
        <p>Or call us on: <a href="tel:+1-555-123-4567">+1 (555) 123-4567</a>.</p>
        <p>General Inquiries: <a href="mailto:info@mycompany.com?subject=Inquiry">info@mycompany.com</a></p>
        <div class="address">
            MyCompany Ltd.<br>
            123 Business Rd, Suite 100<br>
            Businesstown, TX 75001
        </div>
        <div class="social-links">
            <a href="https://linkedin.com/company/mycompany">LinkedIn</a>
            <a href="https://twitter.com/mycompanyhandle">Twitter Profile</a>
        </div>
        <footer>
            Our main office line: (555) 987-6543.
        </footer>
    </body>
</html>
"""

SAMPLE_HTML_NO_INFO = """
<html>
    <head><title>Empty Page</title></head>
    <body><p>Nothing to see here.</p></body>
</html>
"""

SAMPLE_HTML_COMPLEX_FOOTER = """
<html>
    <head><title>Complex Footer Co</title></head>
    <body>
        <p>Main content</p>
        <footer>
            <div>
                <span>Contact:</span>
                <span><a href="tel:123-456-7890">Call Us: 123-456-7890</a></span> |
                <span>Email: <a href="mailto:support@complex.com">support@complex.com</a></span>
            </div>
            <p>&copy; Complex Footer Co. All rights reserved. | 
                <a href="https://linkedin.com/company/complexfooter">LinkedIn</a> |
                Address: 456 Complex Ave, Footer City, ST 90000
            </p>
        </footer>
    </body>
</html>
"""


# --- Fixtures ---

@pytest.fixture
def basic_contact_scraper():
    return HTMLScraper(html_content=SAMPLE_HTML_BASIC_CONTACT, source_url="https://www.mycompany.com/somepage")

@pytest.fixture
def no_info_scraper():
    return HTMLScraper(html_content=SAMPLE_HTML_NO_INFO, source_url="https://www.noinfo.com")

@pytest.fixture
def complex_footer_scraper():
    return HTMLScraper(html_content=SAMPLE_HTML_COMPLEX_FOOTER, source_url="https://www.complex.com")

# --- Initial Tests ---

def test_scraper_initialization(basic_contact_scraper: HTMLScraper, no_info_scraper: HTMLScraper):
    assert basic_contact_scraper.soup is not None
    assert basic_contact_scraper.source_url == "https://www.mycompany.com/somepage"
    assert no_info_scraper.soup is not None # Should handle empty content gracefully

def test_scraper_initialization_with_empty_html():
    scraper = HTMLScraper(html_content="", source_url="https://www.empty.com")
    assert scraper.soup is not None
    assert str(scraper.soup) == "" # Empty soup
    data = scraper.scrape() # Should not fail
    assert data["company_name"] is None # Expect None for fields

# --- Company Name Extraction Tests ---
def test_extract_company_name_og_site_name(basic_contact_scraper: HTMLScraper):
    name = basic_contact_scraper.extract_company_name()
    assert name == "MyCo Official"

def test_extract_company_name_title_fallback():
    html = "<title>Title Company Name | Services</title>"
    scraper = HTMLScraper(html, "http://example.com")
    assert scraper.extract_company_name() == "Title Company Name"

def test_extract_company_name_no_info(no_info_scraper: HTMLScraper):
    assert no_info_scraper.extract_company_name() is None

# --- Phone Number Extraction Tests ---
def test_extract_phone_numbers_basic(basic_contact_scraper: HTMLScraper):
    phones = basic_contact_scraper.extract_phone_numbers()
    assert isinstance(phones, list)
    assert "+1 (555) 123-4567" in phones
    assert "(555) 987-6543" in phones # From footer (assuming broad regex for now)
    assert len(phones) == 2

def test_extract_phone_numbers_complex_footer(complex_footer_scraper: HTMLScraper):
    phones = complex_footer_scraper.extract_phone_numbers()
    assert "123-456-7890" in phones
    assert len(phones) == 1

def test_extract_phone_numbers_no_info(no_info_scraper: HTMLScraper):
    assert no_info_scraper.extract_phone_numbers() == []

# --- Email Extraction Tests ---
def test_extract_emails_basic(basic_contact_scraper: HTMLScraper):
    emails = basic_contact_scraper.extract_emails()
    assert isinstance(emails, list)
    # Emails should be normalized (lowercase) and sorted
    expected_emails = sorted(["contact@mycompany.com", "info@mycompany.com"])
    assert emails == expected_emails

def test_extract_emails_complex_footer(complex_footer_scraper: HTMLScraper):
    emails = complex_footer_scraper.extract_emails()
    assert emails == ["support@complex.com"]

def test_extract_emails_no_info(no_info_scraper: HTMLScraper):
    assert no_info_scraper.extract_emails() == []

# --- Address Extraction Tests (Placeholder) ---
def test_extract_addresses_basic(basic_contact_scraper: HTMLScraper):
    # This test will evolve as extract_addresses is implemented more fully
    # For now, with the basic schema.org example in scraper:
    html_with_schema_address = """
    <html><body>
        <div itemprop itemtype="http://schema.org/PostalAddress">
            <span itemprop="streetAddress">123 Main St</span>,
            <span itemprop="addressLocality">Anytown</span>
        </div>
    </body></html>
    """
    scraper = HTMLScraper(html_with_schema_address, "http://schema.com")
    addresses = scraper.extract_addresses()
    assert addresses == ["123 Main St, Anytown"]

def test_extract_addresses_no_info(no_info_scraper: HTMLScraper):
    assert no_info_scraper.extract_addresses() == []

# --- Social Media Links Extraction Tests ---
def test_extract_social_media_links_basic(basic_contact_scraper: HTMLScraper):
    social_links = basic_contact_scraper.extract_social_media_links()
    assert social_links.get("linkedin") == "https://linkedin.com/company/mycompany"
    assert social_links.get("twitter") == "https://twitter.com/mycompanyhandle"
    assert len(social_links) == 2

def test_extract_social_media_links_complex_footer(complex_footer_scraper: HTMLScraper):
    social_links = complex_footer_scraper.extract_social_media_links()
    assert social_links.get("linkedin") == "https://linkedin.com/company/complexfooter"
    assert len(social_links) == 1

def test_extract_social_media_links_no_info(no_info_scraper: HTMLScraper):
    assert no_info_scraper.extract_social_media_links() == {}

# --- Description Extraction Tests ---
def test_extract_description_basic(basic_contact_scraper: HTMLScraper):
    description = basic_contact_scraper.extract_description()
    assert description == "Contact MyCompany for services."

def test_extract_description_no_info(no_info_scraper: HTMLScraper):
    assert no_info_scraper.extract_description() is None

# --- Canonical URL Extraction Tests ---
def test_extract_canonical_url_basic(basic_contact_scraper: HTMLScraper):
    canonical = basic_contact_scraper.extract_canonical_url()
    assert canonical == "https://www.mycompany.com/contact-us"

def test_extract_canonical_url_no_info(no_info_scraper: HTMLScraper):
    assert no_info_scraper.extract_canonical_url() is None

# --- Full Scrape Method Tests ---
def test_scrape_method_basic(basic_contact_scraper: HTMLScraper):
    data = basic_contact_scraper.scrape()
    assert data["company_name"] == "MyCo Official"
    assert "contact@mycompany.com" in data["emails"]
    assert "+1 (555) 123-4567" in data["phone_numbers"]
    assert data["website"] == "https://www.mycompany.com" # Derived from canonical
    assert data["scraped_from_url"] == "https://www.mycompany.com/somepage"
    assert data["social_media_links"].get("linkedin") is not None

def test_scrape_method_no_info(no_info_scraper: HTMLScraper):
    data = no_info_scraper.scrape()
    assert data["company_name"] is None
    assert data["emails"] == []
    assert data["phone_numbers"] == []
    assert data["website"] == "https://www.noinfo.com" # Derived from source_url
    assert data["social_media_links"] == {}
    assert data["description"] is None
    assert data["canonical_url"] is None


if __name__ == '__main__':
    pytest.main([__file__, "-v"])


```

### 5.9. `requirements.txt`
```txt
# Core
python-dotenv
pydantic

# Logging
loguru

# Web
httpx
beautifulsoup4
# parsel # Optional alternative to BS4, can add later if needed
playwright

# Database (MVP will use SQLite, but good to have base SQLAlchemy)
sqlalchemy
aiosqlite # For async SQLite

# CLI
typer[all]

# Testing
pytest
pytest-mock
pytest-cov
pytest-html # For HTML test reports
pytest-asyncio # For async tests
pydantic-settings

tldextract

respx
```

### 5.10. `lead_gen_pipeline/__init__.py`
```python
# This file is currently empty, serving only to mark the directory as a package.
```

### 5.11. Other Files
The following files also exist and are part of the project setup:
- `.env` (local, ignored by Git - contains secrets/local overrides)
- `.env.example` (template for `.env`)
- `.gitignore` (standard Python .gitignore)
- `README.md` (project README, can be simple for now)
- `LICENSE` (e.g., MIT License)
- `cli_mvp.py` (placeholder, empty)
- `run_pipeline_mvp.py` (placeholder, empty)
- `data/urls_seed.csv` (placeholder, empty or with example URLs)
- `logs/app.log` (will be created by logger)
- `tests/__init__.py`, `tests/integration/__init__.py`, `tests/unit/__init__.py` (empty package markers)
