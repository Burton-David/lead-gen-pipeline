# B2B Lead Generation Pipeline - Developer Documentation
**Version:** 0.2.2 (MVP Core Flow Tested - Scraper Enhancement In Progress with Library-First Approach)
**Last Updated:** 2025-05-27 16:08 EDT

## 1. Project Overview

This project aims to build an advanced, production-ready B2B lead generation pipeline. The system will scrape, enrich, and store business leads from diverse web sources, forming the primary engine for gathering comprehensive raw lead data.

### 1.1. Core Mission & Vision

The ultimate goal is to create a system capable of highly effective and stealthy data acquisition. Future iterations will focus on bypassing advanced anti-bot measures, utilizing sophisticated browser fingerprinting techniques, and achieving near-undetectable crawling.

This pipeline is focused on the efficient and reliable gathering and initial storage of **high-quality raw lead data**. Subsequent, separate programs will handle detailed data cleaning, verification (e.g., confirming business operating status, correct business type), and further enrichment to produce clean, actionable lists of target businesses with all necessary OSINT contact information. Advanced techniques, potentially including image processing for deeper business categorization, are envisioned for later stages.

### 1.2. MVP Goal & Current Focus

The initial Minimum Viable Product (MVP) established a functional system for crawling, basic scraping (using custom regexes in `scraper.py`), and storing data in an SQLite database. Integration testing of the `run_pipeline_mvp.py` script validated this core data flow.

However, these tests, along with our development iterations, highlighted the need for significant enhancements to `scraper.py` to improve its accuracy, robustness, and maintainability, particularly for extracting complex data points like phone numbers, addresses, and company names from varied HTML structures.

The **current immediate focus** is a dedicated effort to:
1.  Thoroughly enhance `scraper.py` by adopting a **library-first approach** for parsing complex data. This begins with integrating the `phonenumbers` library for `extract_phone_numbers`. Subsequent methods will also prioritize well-vetted libraries over custom-built complex regexes where appropriate.
2.  Expand and refine unit tests in `tests/unit/test_scraper.py` to ensure high-quality raw data collection and cover diverse edge cases, reflecting the capabilities of the integrated libraries.
3.  Ensure the `run_pipeline_mvp.py` and integration tests (`tests/integration/test_pipeline_flow.py`) continue to validate the overall pipeline with these scraper enhancements.

This strategic shift aims to build a more robust, elegant, and maintainable scraper, aligning with the project's goal of producing the best possible system.

## 2. Core Principles

* **Modularity:** Each component (crawler, scraper, database, etc.) should be self-contained with clear responsibilities.
* **Testability:** Comprehensive unit, integration, and (eventually) end-to-end tests are crucial. Every piece of code should be testable. Test cases should cover a wide range of scenarios, including edge cases.
* **Robustness & Resilience:** The system must handle errors gracefully, implement retries where appropriate, and be resilient to varied and messy web data.
* **Data Quality:** Strive for the highest accuracy and completeness in scraped raw data. This is the paramount concern for the current `scraper.py` enhancements.
* **Elegance & Maintainability:** Write clean, well-documented, and well-structured code. Prioritize using established libraries for common complex tasks (e.g., phone number parsing, address parsing) over reinventing the wheel, to leverage community-vetted solutions and simplify custom logic.
* **Stealth & Politeness (Evolving):** The crawler must mimic human behavior and respect website resources. Advanced stealth is a key future goal. For now, ethical considerations and basic politeness (rate limiting, `robots.txt`) are key.
* **Extensibility:** The architecture should facilitate adding new parsers, data sources, enrichment strategies, and adapting to new domains with minimal friction.
* **Ethical Considerations:** Prioritize ethical data sourcing and respect `robots.txt` as configured.

## 3. Module Status & Responsibilities

### 3.1. `lead_gen_pipeline/config.py`
* **Status:** ✅ Complete & Tested
* **Responsibilities:** Manages all application settings using Pydantic, including nested configurations for crawler, logging, and database. Loads from `.env` files and environment variables.

### 3.2. `lead_gen_pipeline/utils.py`
* **Status:** ✅ Complete & Tested
* **Responsibilities:** Provides shared utility functions:
    * Advanced logging setup with Loguru (console, file, error file, rotation).
    * `async_retry` decorator with exponential backoff and jitter.
    * Text cleaning (`clean_text`) and normalization/extraction for emails (`normalize_email`, `extract_emails_from_text` using a robust regex).
    * URL utilities (`extract_domain` using `tldextract`, `make_absolute_url`).
    * `DomainRateLimiter` class for controlling request frequency per domain and overall concurrency within specific contexts.

### 3.3. `lead_gen_pipeline/crawler.py`
* **Status:** ✅ Complete & Tested (Core HTTPX & Playwright fetching, Robots.txt handling)
* **Responsibilities:** Fetches web page content.
    * Supports both `HTTPX` (for speed and simple pages) and `Playwright` (for JavaScript-heavy sites).
    * Manages User-Agent rotation.
    * Implements `robots.txt` fetching, parsing, caching (LRU), and adherence.
    * Integrates with `DomainRateLimiter` from `utils.py`.
    * Uses `async_retry` for fetch attempts.
    * Basic CAPTCHA keyword detection.
    * Handles proxy configuration from `config.py`.

### 3.4. `lead_gen_pipeline/scraper.py`
* **Status:** ⚠️ **Under Enhancement for Robustness & Accuracy.**
    * Baseline structure for various extraction methods (`extract_company_name`, `extract_emails`, `extract_addresses`, `extract_social_media_links`, `extract_description`, `extract_canonical_url`) is in place.
    * **Current Focus:** Refactoring `extract_phone_numbers` to integrate the `phonenumbers` library for robust parsing, validation, and formatting.
    * **Next Steps:** Systematically review and enhance other extraction methods, prioritizing a library-first approach where applicable (e.g., for addresses) to improve accuracy, handle more edge cases, and simplify custom logic. Expand unit tests significantly for each method.
* **Responsibilities:** Parses HTML content (provided by `crawler.py`) to extract structured data points. Aims for high accuracy and comprehensive coverage of varied HTML structures.

### 3.5. `lead_gen_pipeline/models.py`
* **Status:** ✅ Complete & Tested (MVP - `Lead` model)
* **Responsibilities:** Defines SQLAlchemy data models. Currently includes the `Lead` model with fields for all scraped data points, using `JSON` type for lists/dicts and timezone-aware datetimes.

### 3.6. `lead_gen_pipeline/database.py`
* **Status:** ✅ Complete & Tested (MVP - SQLite storage, dynamic engine/session factory)
* **Responsibilities:** Handles all database interactions using SQLAlchemy Core and ORM with `aiosqlite` for asynchronous operations with SQLite.
    * `get_engine()`: Creates and returns the SQLAlchemy async engine.
    * `get_async_session_local()`: Provides a session factory.
    * `init_db()`: Creates database tables based on models.
    * `save_lead()`: Saves a `Lead` object to the database, managing local session transactions.
    * `get_db()`: Async generator for providing DB sessions (e.g., for FastAPI dependencies).

### 3.7. `lead_gen_pipeline/llm_handler.py`
* **Status:** ⏳ To Do (Placeholder for future MVP+)
* **Responsibilities (Planned):** Interface for interactions with local or remote Large Language Models (LLMs) for tasks like advanced data cleaning, categorization, or sentiment analysis on scraped descriptions.

### 3.8. `run_pipeline_mvp.py`
* **Status:** ✅ Initial Orchestration Implemented & Integration Tested.
* **Responsibilities:** Orchestrates the MVP workflow:
    * Reads seed URLs from a CSV file specified in `config.py`.
    * Uses `AsyncWebCrawler` to fetch content.
    * Uses `HTMLScraper` to parse HTML and extract data.
    * Uses `database.py` functions to initialize the DB and save extracted `Lead` data.
    * Manages overall pipeline concurrency using `asyncio.Semaphore`.
    * Will be validated further after `scraper.py` improvements are complete.

### 3.9. `cli_mvp.py`
* **Status:** ⏳ To Do
* **Responsibilities (Planned):** Basic command-line interface (likely using Typer) for running the pipeline (`run_pipeline_mvp.py`), potentially allowing overrides for input file, database location, etc.

### 3.10. Test Modules
* **`tests/unit/test_config.py`**: ✅ Complete & Tested.
* **`tests/unit/test_utils.py`**: ✅ Complete & Tested.
* **`tests/unit/test_crawler.py`**: ✅ Complete & Tested.
* **`tests/unit/test_models.py`**: ✅ Complete & Tested.
* **`tests/unit/test_database.py`**: ✅ Complete & Tested.
* **`tests/unit/test_scraper.py`**: ⚠️ **Under Active Development.** Unit tests are being significantly expanded and refined in parallel with `scraper.py` enhancements. Current focus is on comprehensive tests for `extract_phone_numbers` using various formats and edge cases relevant to the `phonenumbers` library.
* **`tests/integration/test_pipeline_flow.py`**: ✅ Initial version implemented. Validated the core MVP data flow (crawl -> scrape -> save). Assertions within this test will be updated and expanded as `scraper.py` is enhanced to reflect improved data extraction capabilities. This test remains crucial for verifying end-to-end pipeline integrity.
* **`tests/unit/test_llm_handler.py`**: ⏳ To Do.
* **`tests/unit/test_cli_mvp.py`**: ⏳ To Do.

## 4. Coding Style & Conventions

* **PEP 8:** Adhere to PEP 8 style guidelines. Use a linter like Flake8 or Ruff.
* **Type Hinting:** Use type hints for all function signatures and complex variable assignments (Python 3.9+).
* **Logging:** Use the configured Loguru instance from `utils.py` for all logging. Add contextual information to logs.
* **Docstrings:** Write clear docstrings for all modules, classes, and functions (Google style or reStructuredText).
* **Comments:** Use comments to explain complex logic or non-obvious decisions.
* **Modularity:** Keep functions and classes focused on a single responsibility.
* **Error Handling:** Implement robust error handling (try-except blocks) for I/O operations, API calls, and parsing logic. Log errors appropriately.
* **Configuration:** All configurable parameters (timeouts, file paths, credentials, etc.) must be managed via `config.py`. No hardcoded sensitive values.
* **Version Comments:** Include a version and last updated timestamp comment at the top of each Python file, e.g., `# Version: Gemini-YYYY-MM-DD HH:MM EDT`.

## 5. Testing Strategy

* **Framework:** Pytest.
* **Plugins:** `pytest-asyncio` (for async tests), `pytest-cov` (for coverage), `pytest-mock` (for mocking). `respx` for mocking HTTPX requests in crawler tests.
* **Unit Tests:** Each module must have comprehensive unit tests covering its functions and classes. Focus on edge cases and varied inputs. Located in `tests/unit/`.
    * `scraper.py` unit tests are currently a high priority for expansion to cover diverse HTML structures and data formats for each extraction method, aligning with library-based parsing.
* **Integration Tests:** Test the interaction between different components (e.g., crawler fetching content that the scraper then parses, pipeline orchestrating crawl-scrape-save). Located in `tests/integration/`.
    * `test_pipeline_flow.py` is the primary integration test for the MVP. Its mock data and assertions will be key to validating scraper improvements.
* **Coverage:** Aim for high test coverage (e.g., >90%).
* **CI/CD:** (Future) Integrate tests into a CI/CD pipeline (e.g., GitHub Actions).

## 6. Common Pitfalls to Avoid

* **Hardcoding:** Avoid hardcoding file paths, URLs, credentials, or any configurable values. Use `config.py`.
* **Ignoring Errors:** Catch exceptions gracefully and log them. Don't let the pipeline crash silently.
* **Blocking Operations:** Ensure all I/O operations (network requests, database calls) are asynchronous in the core pipeline.
* **Overly Complex Regex:** For complex parsing tasks (e.g., phone numbers, addresses), prefer using established libraries over writing and maintaining highly complex, brittle regular expressions. (Current strategic shift)
* **Lack of Rate Limiting/Politeness:** Always implement politeness measures when crawling.
* **Insufficient Testing:** Lack of thorough tests, especially for edge cases in the scraper.

## 7. Full Vision Roadmap & Future Enhancements (Post-MVP - Subject to Refinement)

This reflects longer-term goals beyond the immediate MVP and scraper enhancements.

### Phase 1: Solidify Core Scraping & MVP (Current Focus)
* Thoroughly enhance `scraper.py` (library-first approach, comprehensive unit tests).
* Refine `run_pipeline_mvp.py` and integration tests.
* Develop basic `cli_mvp.py`.
* Small-scale live test run and validation.
* Documentation update (README, DEV_DOCUMENTATION).

### Phase 2: Advanced Stealth & Crawler Robustness
* **Proxy Integration:** Sophisticated proxy rotation (e.g., BrightData, ScraperAPI, custom).
* **Browser Fingerprinting:** Implement techniques to modify Playwright's fingerprint (navigator properties, WebGL, canvas, fonts, user-agent generation linked to fingerprint).
* **CAPTCHA Handling:** Integrate with services like 2Captcha or explore advanced interaction methods.
* **Behavioral Mimicry:** Simulate human-like mouse movements, scrolling, typing, and realistic delays.
* **Distributed Crawling (Conceptual):** Design for potential distribution (e.g., Celery, RQ, or cloud functions) for larger scale.

### Phase 3: Enrichment & Data Quality Enhancement
* **`enricher.py` Development:**
    * Email pattern detection and validation.
    * Domain analysis (WHOIS, domain age).
    * Cross-referencing with other data sources (e.g., public APIs, LinkedIn if feasible and ethical).
    * Confidence scoring for scraped data.
* **`llm_handler.py` Integration:**
    * LLM-based data cleaning, normalization, and categorization (e.g., industry from description).
    * Sentiment analysis on company descriptions.
    * Summarization.
* **Image Processing:**
    * Logo detection and recognition for company identification/verification.
    * Image-based business categorization (e.g., storefront type).

### Phase 4: Scalability, Deployment & Operations
* **Database Scaling:** Consider migrating from SQLite to PostgreSQL or other scalable DB if volume demands. Implement Alembic for migrations.
* **Containerization:** Dockerfile and `docker-compose.yml` for easy deployment and environment consistency.
* **Scheduling:** `scheduler.py` for cron-based or event-driven pipeline runs.
* **Monitoring & Alerting:** Integrate with logging/monitoring tools (e.g., ELK stack, Prometheus/Grafana, Sentry) for production. Slack/Discord notifications.
* **API Layer:** Optional FastAPI layer to serve collected and processed leads.
* **Admin Interface:** More advanced CLI or simple web UI for managing seed URLs, viewing stats, retrying errors.

This document will evolve. Let's keep it updated to reflect our progress and refined strategies.