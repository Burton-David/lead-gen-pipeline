B2B Lead Generation Pipeline - Developer Documentation
Version: 0.2.1 (MVP Core Flow Tested - Scraper Enhancement In Progress)
Last Updated: 2025-05-26 21:17 EDT

Project Overview
This project aims to build an advanced, production-ready B2B lead generation pipeline. The system will scrape, enrich, and store business leads from diverse web sources.

Core Mission & Vision:
The ultimate goal is to create a system capable of highly effective and stealthy data acquisition. Future iterations will focus on bypassing advanced anti-bot measures, utilizing sophisticated browser fingerprinting techniques, and achieving near-undetectable crawling. This pipeline will be the primary engine for gathering comprehensive raw lead data. Subsequent, separate programs will handle data cleaning, verification (e.g., confirming business operating status, correct business type), and further enrichment to produce a clean, actionable list of target businesses with all necessary OSINT contact information. Advanced techniques, potentially including image processing for deeper business categorization, are envisioned for later stages to enhance the quality and detail of the collected leads.

MVP Goal & Current Focus:
The initial Minimum Viable Product (MVP) focused on establishing a functional system for crawling, basic scraping, and storing data. Integration testing of the run_pipeline_mvp.py script has validated this core flow. However, these tests also highlighted the need for significant enhancements to scraper.py to improve its accuracy and robustness in extracting various data points (e.g., phone numbers, company names).
The current immediate focus is a dedicated effort to thoroughly enhance scraper.py and its unit tests to ensure high-quality raw data collection before proceeding with broader pipeline execution or CLI development.

Core Principles

Modularity: Each component (crawler, scraper, database, etc.) should be self-contained and have clear responsibilities.

Testability: Every piece of code should be testable. Comprehensive unit and integration tests are crucial.

Stealth & Politeness (Evolving): The crawler must mimic human behavior. Advanced stealth is a key future goal.

Robustness & Resilience: The system should handle errors gracefully and implement retries.

Extensibility: The architecture should facilitate adding new parsers, enrichment strategies, and adapting to new domains.

Data Quality: Strive for accuracy in scraped raw data. This is the current enhancement focus for scraper.py.

Ethical Considerations: Prioritize ethical data sourcing.

Maintainability: Write clean, well-documented code.

Module Status & Responsibilities

lead_gen_pipeline/config.py

Status: ✅ Complete & Tested

Responsibilities: Manages all application settings.

lead_gen_pipeline/utils.py

Status: ✅ Complete & Tested

Functionality: Logging, async retry, text/URL utilities, domain rate limiter.

lead_gen_pipeline/crawler.py

Status: ✅ Complete & Tested (HTTPX, Playwright, Robots.txt)

Responsibilities: Fetches web page content.

lead_gen_pipeline/scraper.py

Status: ⚠️ Under Enhancement for Robustness & Accuracy (MVP methods in place, focused refinement in progress)

Responsibilities: Parses HTML content to extract structured data.

Current Focus: Improving extract_phone_numbers, extract_company_name, and other methods for better accuracy and coverage of varied HTML structures. Expanding unit tests significantly.

lead_gen_pipeline/models.py

Status: ✅ Complete & Tested (MVP - Lead model)

Responsibilities: Defines SQLAlchemy data models (Lead model for MVP).

lead_gen_pipeline/database.py

Status: ✅ Complete & Tested (MVP - SQLite storage, dynamic engine/session factory)

Responsibilities: Handles database interactions (init, save) using SQLAlchemy with aiosqlite.

lead_gen_pipeline/llm_handler.py

Status: ⏳ To Do (Placeholder for MVP)

Responsibilities (Planned): Interface for local LLM interactions.

run_pipeline_mvp.py

Status: ✅ Initial Orchestration Implemented & Integration Tested (Revealed need for scraper enhancements)

Responsibilities: Orchestrates the MVP workflow: read seed URLs, crawl, scrape, store. Will be revisited after scraper improvements.

cli_mvp.py

Status: ⏳ To Do

Responsibilities (Planned): Basic Typer CLI for running the pipeline.

tests/integration/test_pipeline_flow.py

Status: ✅ Initial version implemented. Validated core pipeline data flow. Currently highlights areas for scraper.py improvement. Assertions will be updated as scraper is enhanced.

Coding Style & Conventions

(Content remains the same as previous version - PEP 8, Type Hinting, Logging, Docstrings, etc.)

Testing Strategy

(Content remains the same as previous version - Framework, Plugins, Unit Tests, Integration Tests, etc. Emphasize that scraper unit tests are currently being expanded.)

Common Pitfalls to Avoid

(Content remains the same as previous version)

Full Vision Roadmap & Future Enhancements (Post-MVP)

(Content remains the same as previous version, still reflecting the long-term goals including advanced stealth, image processing, etc.)

This document will evolve as we build. Let's keep it updated.