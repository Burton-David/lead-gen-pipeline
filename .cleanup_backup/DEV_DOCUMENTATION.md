Developer Documentation: Lead Generation Scraper
Version: 0.3.0 (Strategic Refinement & ML Integration Planning)
Last Updated: 2025-05-28

0. Document Purpose
This document outlines the development plan, current project state, core principles, module responsibilities, and future roadmap for the B2B Lead Generation Pipeline. It is intended for developers working on the project to ensure alignment and maintain a shared understanding of goals and practices.

1. Project Overview
This project aims to build an advanced, production-ready B2B lead generation pipeline. The system will scrape, enrich, and store business leads from diverse web sources, forming the primary engine for gathering comprehensive raw lead data.

1.1. Core Mission & Vision
The ultimate goal is to create a system capable of highly effective and stealthy data acquisition. Future iterations will focus on bypassing advanced anti-bot measures, utilizing sophisticated browser fingerprinting techniques, and achieving near-undetectable crawling.

This pipeline is focused on the efficient and reliable gathering and initial storage of high-quality raw lead data. Subsequent, separate programs will handle detailed data cleaning, verification (e.g., confirming business operating status, correct business type), and further enrichment to produce clean, actionable lists of target businesses with all necessary OSINT contact information. Advanced techniques, potentially including image processing for deeper business categorization, are envisioned for later stages.

1.2. MVP Goal & Current Focus (Pre-Strategic Shift)
The initial Minimum Viable Product (MVP) established a functional system for crawling, basic scraping (using custom regexes in scraper.py), and storing data in an SQLite database. Integration testing of the run_pipeline_mvp.py script validated this core data flow.

However, these tests, along with development iterations, highlighted the need for significant enhancements to scraper.py to improve its accuracy, robustness, and maintainability.

1.3. Strategic Shift & Current Immediate Focus
A strategic shift has been made to enhance scraper.py by adopting a library-first approach for parsing complex data and to plan for Machine Learning integration for advanced extraction and data quality.

The current immediate focus (as of this document update) is:

Thoroughly enhance scraper.py by systematically addressing failing unit tests, prioritizing robust parsing of phone numbers, emails, company names, and social media links, leveraging specialized libraries where effective.

Expand and refine unit tests in tests/unit/test_scraper.py to ensure high-quality raw data collection and cover diverse edge cases.

Refine the strategy for international address parsing due to the current unavailability of libpostal, focusing on robust US address parsing and safe storage of unparsed international address data for future ML processing.

Lay the groundwork for future ML integration by identifying suitable tasks and models.

2. Core Principles
Modularity: Each component (crawler, scraper, database, etc.) should be self-contained with clear responsibilities.

Testability: Comprehensive unit, integration, and (eventually) end-to-end tests are crucial. Every piece of code should be testable. Test cases should cover a wide range of scenarios, including edge cases.

Robustness & Resilience: The system must handle errors gracefully, implement retries where appropriate, and be resilient to varied and messy web data.

Data Quality: Strive for the highest accuracy and completeness in scraped raw data. This is the paramount concern for the current scraper.py enhancements and future ML integration. False positives must be aggressively minimized.

Elegance & Maintainability: Write clean, well-documented, and well-structured code. Prioritize using established libraries for common complex tasks over reinventing the wheel.

Stealth & Politeness (Evolving): The crawler must mimic human behavior and respect website resources. Advanced stealth is a key future goal. For now, ethical considerations and basic politeness (rate limiting, robots.txt) are key.

Extensibility: The architecture should facilitate adding new parsers, data sources, enrichment strategies, and adapting to new domains with minimal friction.

Ethical Considerations: Prioritize ethical data sourcing and respect robots.txt as configured.

3. Current Project State (Snapshot)
scraper.py Version: v15_pytest_feedback (based on previous v12_holistic_fixes with targeted fixes).

test_scraper.py Version: v12_updates (unit tests driving development).

placeholder_data.py Version: v3_combined (comprehensive list of excludable generic terms).

Supporting Files: utils.py (helper functions), config.py (settings).

Last Known Test Results (Post-v15_pytest_feedback application): 38 failed, 65 passed (out of 103 total).

Note: This reflects the state reported by the user after the v15_pytest_feedback code was provided and before further debugging of those specific 38 failures.

Primary Development Method: Iterative refinement of scraper.py by systematically addressing failing unit tests in test_scraper.py.

4. Progress & Recent Changes (Leading to v15_pytest_feedback)
The project has been undergoing iterative development with a strong focus on improving the accuracy and robustness of each data extraction function within scraper.py. Recent efforts have concentrated on:

Foundational Text Extraction (_extract_text_content): Ensuring correct text assembly from complex/nested HTML, proper Unicode normalization, and handling of various whitespace and hyphen types.

Phone Number Extraction (extract_phone_numbers): Addressing issues with vanity number parsing, extension handling, cleaning of trailing words, and improving parsing for various formats.

Email Extraction (extract_emails): Enhancing deobfuscation logic and Cloudflare email protection decoding.

Company Name Extraction (extract_company_name): Refining copyright notice parsing and heuristics.

Social Media Link Extraction (extract_social_media_links): Improving schemeless URL handling and domain/path matching.

General Robustness: Addressing runtime errors.

5. Module Status & Responsibilities
5.1. lead_gen_pipeline/config.py
Status: ✅ Complete & Tested

Responsibilities: Manages all application settings using Pydantic, including nested configurations for crawler, logging, and database. Loads from .env files and environment variables.

5.2. lead_gen_pipeline/utils.py
Status: ✅ Complete & Tested

Responsibilities: Provides shared utility functions:

Advanced logging setup with Loguru.

async_retry decorator.

Text cleaning (clean_text), email normalization/extraction (normalize_email, extract_emails_from_text).

URL utilities (extract_domain, make_absolute_url).

DomainRateLimiter class.

5.3. lead_gen_pipeline/crawler.py
Status: ✅ Complete & Tested (Core HTTPX & Playwright fetching, Robots.txt handling)

Responsibilities: Fetches web page content, supporting HTTPX and Playwright. Manages User-Agents, robots.txt adherence, rate limiting, retries, basic CAPTCHA detection, and proxy configuration.

5.4. lead_gen_pipeline/scraper.py
Status: ⚠️ Under Active Enhancement for Robustness, Accuracy, and Strategic Realignment.

Baseline extraction methods are in place.

Current Focus: Systematically addressing the 38 failing unit tests from the last run. This involves deep debugging of _extract_text_content, extract_phone_numbers, extract_emails, extract_company_name, extract_social_media_links, and extract_addresses to handle diverse edge cases and improve parsing logic.

Strategic Shift: Adopting a library-first approach where effective (e.g., phonenumbers). Revising address parsing strategy due to libpostal unavailability (see Section 7.2). Planning for future ML integration (see Section 7.3).

Responsibilities: Parses HTML content to extract structured data points with high accuracy.

5.5. lead_gen_pipeline/models.py
Status: ✅ Complete & Tested (MVP - Lead model)

Responsibilities: Defines SQLAlchemy data models. Currently includes the Lead model.

5.6. lead_gen_pipeline/database.py
Status: ✅ Complete & Tested (MVP - SQLite storage, dynamic engine/session factory)

Responsibilities: Handles database interactions using SQLAlchemy with aiosqlite. Provides session management, table initialization, and lead saving logic.

5.7. lead_gen_pipeline/llm_handler.py
Status: ⏳ To Do (Placeholder for future ML integration)

Responsibilities (Planned): Interface for interactions with local or remote Large Language Models (LLMs) for tasks like advanced data cleaning, categorization, sentiment analysis, or ML-driven parsing (e.g., addresses).

5.8. run_pipeline_mvp.py
Status: ✅ Initial Orchestration Implemented & Integration Tested.

Responsibilities: Orchestrates the MVP workflow (read URLs, crawl, scrape, save). Will be validated further after scraper.py improvements.

5.9. cli_mvp.py
Status: ⏳ To Do

Responsibilities (Planned): Basic command-line interface (e.g., Typer) for running the pipeline.

5.10. Test Modules
tests/unit/test_config.py: ✅ Complete & Tested.

tests/unit/test_utils.py: ✅ Complete & Tested.

tests/unit/test_crawler.py: ✅ Complete & Tested.

tests/unit/test_models.py: ✅ Complete & Tested.

tests/unit/test_database.py: ✅ Complete & Tested.

tests/unit/test_scraper.py: ⚠️ Under Active Development & Refinement. Unit tests are critical and are being updated/expanded in lockstep with scraper.py enhancements. The current 38 failures are the primary focus.

tests/integration/test_pipeline_flow.py: ✅ Initial version implemented. Assertions will be updated as scraper.py improves.

tests/unit/test_llm_handler.py: ⏳ To Do.

tests/unit/test_cli_mvp.py: ⏳ To Do.

6. Coding Style & Conventions
PEP 8: Adhere to PEP 8 style guidelines. Use a linter like Flake8 or Ruff.

Type Hinting: Use type hints for all function signatures and complex variable assignments (Python 3.9+).

Logging: Use the configured Loguru instance from utils.py for all logging. Add contextual information.

Docstrings: Write clear docstrings for all modules, classes, and functions (Google style or reStructuredText).

Comments: Use comments to explain complex logic or non-obvious decisions.

Modularity: Keep functions and classes focused on a single responsibility.

Error Handling: Implement robust error handling (try-except blocks). Log errors appropriately.

Configuration: All configurable parameters must be managed via config.py.

Version Comments: Include a version and last updated timestamp comment at the top of each Python file.

7. Revised Development Plan & Phased Roadmap
This roadmap integrates the strategic decisions regarding address parsing and ML integration into a phased approach.

Phase 1: Solidify Core Scraping & MVP (Current Focus)
Objective: Achieve a high pass rate for test_scraper.py by robustly enhancing all extraction methods in scraper.py.

Tasks:

Systematic Debugging (Immediate Priority):

Thoroughly analyze and fix the 38 failing unit tests from the v15_pytest_feedback stage.

Prioritize _extract_text_content, extract_phone_numbers, extract_emails, extract_company_name, extract_social_media_links.

Address Extraction Refinement (Short-Term):

Strengthen usaddress usage for US patterns.

Implement the strategy of storing cleaned, unparsed text blocks for non-US/ambiguous addresses (see Section 7.2.1 below).

Library-First Principle: Continuously evaluate and integrate well-vetted libraries for parsing tasks where beneficial.

Unit Test Expansion: Ensure comprehensive test coverage for all scraper functionalities.

Refine run_pipeline_mvp.py and tests/integration/test_pipeline_flow.py based on scraper enhancements.

Develop basic cli_mvp.py.

Conduct small-scale live test runs for validation.

Keep documentation (README, this document) updated.

Phase 2: Advanced Stealth, Crawler Robustness & Initial ML Exploration
Objective: Enhance crawler stealth and begin exploring ML for data quality improvement.

Tasks:

Crawler Enhancements:

Sophisticated proxy rotation integration.

Browser fingerprinting modifications (Playwright).

Research CAPTCHA handling services/techniques.

Simulate more human-like browsing behavior.

Initial ML for Company Name Augmentation:

Integrate a pretrained NER model (e.g., spaCy) into extract_company_name as a fallback or validation step (see Section 7.3.1).

Evaluate impact on accuracy and false positives.

Data Collection for Address Parsing ML: Begin curating the dataset of unparsed international address strings collected in Phase 1.

Phase 3: ML Model Development & Enrichment Capabilities
Objective: Develop and integrate custom ML models, particularly for address parsing, and expand data enrichment.

Tasks:

ML for Address Parsing (Long-Term):

Research, develop, or fine-tune a sequence labeling model to parse the collected international address strings into components (street, city, postcode, country) (see Section 7.2.2).

enricher.py Development (Conceptual):

Domain analysis (WHOIS, etc.).

Cross-referencing with public APIs.

Confidence scoring for scraped data.

llm_handler.py Integration (Conceptual):

Explore LLMs for advanced data cleaning, normalization, industry categorization from descriptions, sentiment analysis.

Image Processing (Conceptual):

Logo detection for company verification.

Image-based business categorization.

Phase 4: Scalability, Deployment & Operations
Objective: Prepare the pipeline for larger-scale operation and robust deployment.

Tasks:

Database Scaling: Consider migration from SQLite if volume demands (e.g., PostgreSQL). Implement Alembic for migrations.

Containerization: Dockerfile and docker-compose.yml.

Scheduling: scheduler.py for automated pipeline runs.

Monitoring & Alerting: Integration with logging/monitoring tools.

API Layer (Optional): FastAPI to serve collected leads.

Admin Interface: Advanced CLI or simple web UI.

Distributed Crawling (Conceptual): Design for potential distribution.

7.1. Core Scraping Refinement (Ongoing Detail - Part of Phase 1)
Objective: Continue to systematically address and fix the remaining failing unit tests in test_scraper.py.

Priority:

Solidify _extract_text_content as it's foundational.

Iteratively enhance extract_phone_numbers, extract_emails, extract_company_name, and extract_social_media_links based on detailed analysis of test failures.

Ensure solutions are robust, handle edge cases, and avoid introducing regressions.

7.2. Address Extraction Strategy (Revised Detail - Spans Phase 1 & 3)
Challenge: libpostal unavailability. usaddress is US-specific.

Revised Strategy:

7.2.1. Short-to-Medium Term (Phase 1):

US Addresses: Continue to use usaddress_tag_func for strong US patterns.

Non-US/Ambiguous Addresses: Extract, clean (_extract_text_content), and store the most complete address-like text block unparsed. This preserves data for future ML parsing.

Optional - Geocoding API (Future Consideration, Post-Phase 1): Integrate a third-party geocoding service as an optional enrichment step (asynchronous/batch) for higher accuracy if feasible (cost, rate limits, ToS).

7.2.2. Long-Term (Phase 3 - Machine Learning Approach):

Use collected raw/semi-parsed international address strings to train/fine-tune an ML model (e.g., sequence labeling with transformers) for parsing into components (street, city, postcode, country).

7.3. Advanced Information Extraction with Machine Learning (Future Roadmap Detail - Spans Phase 2 & 3)
Rationale: Enhance extraction for non-tagged/complex data, improve confidence, and minimize false positives.

Potential ML Applications & Phasing:

Address Parsing (Phase 3): Primary ML use case (see 7.2.2).

Company Name Augmentation & Validation (Phase 2-3): Use NER (e.g., spaCy, fine-tuned BERT) for ORG mentions to augment rule-based extraction.

Contact Person & Role Extraction (Phase 3+): NER for PERSON and classification for roles.

Product/Service Category Inference (Phase 3+): Text classification on descriptions.

Disambiguation & Confidence Scoring (Phase 3+): ML to identify "main" phone numbers or assign confidence scores to extractions.

Implementation Approach: Incremental integration, fine-tuning for specific tasks, performance considerations, modular design.

7.4. Data Quality and False Positives (Cross-Cutting Concern)
Overarching Principle: Accuracy and cleanliness are paramount.

Strategy: Refined rules, comprehensive filtering (placeholder_data.py), ML models optimized for precision, validation layers.

8. Testing Strategy
Framework: Pytest.

Plugins: pytest-asyncio, pytest-cov, pytest-mock, respx.

Unit Tests: Comprehensive tests for each module in tests/unit/. test_scraper.py is a high priority for ongoing expansion.

Integration Tests: Test component interactions in tests/integration/. test_pipeline_flow.py validates the end-to-end MVP flow.

Coverage: Aim for >90%.

CI/CD (Future): Integrate tests into a CI/CD pipeline.

9. Common Pitfalls to Avoid
Hardcoding: Use config.py for all configurable values.

Ignoring Errors: Catch exceptions gracefully and log them.

Blocking Operations: Ensure I/O is asynchronous in the core pipeline.

Overly Complex Regex: Prefer established libraries for complex parsing (current strategic shift).

Lack of Rate Limiting/Politeness: Implement and respect politeness measures.

Insufficient Testing: Crucial to have thorough tests, especially for scraper edge cases.

10. Next Immediate Steps (Reiteration)
Detailed Analysis of Current Failures: Thoroughly review pytest output for the 38 failing tests.

Systematic Debugging: Address these failures in scraper.py.

Iterative Testing: Continue the code-test-refine cycle.

Documentation: Keep this document updated.