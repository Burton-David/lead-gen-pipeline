# 🚀 btl-lead-gen-pipeline 🚀

A Python-based data pipeline that scrapes B2B lead data (company names, websites, emails, etc.), cleans, enriches, and stores it. Designed for stealth, scalability, and ethical web scraping.

## ✨ Features

* **Stealthy Crawling**: Mimics real user behavior with rotating User-Agents, screen sizes (Playwright), IP rotation (via 3rd party proxies), adaptive rate limiting per domain.
* **Dual Crawling Engine**: Uses `httpx` for fast static content and `Playwright` for JavaScript-heavy sites.
* **Modular Scraping**: Easily pluggable site-specific parsers and a generic fallback parser.
* **Data Enrichment**: Strategies like email pattern prediction, domain age analysis. (LinkedIn enrichment is a placeholder due to its complexity and risk).
* **Structured Storage**: Saves data to a SQL database (PostgreSQL or SQLite) using SQLAlchemy async.
* **Concurrency**: Leverages `asyncio` for high-throughput I/O-bound tasks.
* **Resilience**: Implements retries with exponential backoff and jitter.
* **Ethical Considerations**: Basic `robots.txt` awareness (placeholder), configurable delays, and rate limits.
* **Containerized**: `Dockerfile` and `docker-compose.yml` for easy deployment.
* **CLI & API**: `Typer` for CLI operations (run pipeline, export data) and an optional `FastAPI` layer to serve leads or trigger jobs.
* **Database Migrations**: Uses `Alembic` for managing schema changes.
* **Comprehensive Logging**: `Loguru` for structured, rotating logs.

## 🏗️ System Architecture

```mermaid
graph TD
    A[urls.txt] --> B(run_pipeline.py / cli.py);
    B -- Manages --> C{Crawler (crawler.py)};
    C -- HTTPX/Playwright --> D[Target Websites];
    N[User-Agents/Proxies/CAPTCHA Solvers] <--> C;
    C -- Raw HTML --> E{Scraper (scraper.py)};
    J[utils.py] -- Helpers & Rate Limiter --> C;
    J -- Helpers --> E;
    J -- Helpers --> F;
    E -- Raw Leads List --> F{Enricher (enricher.py)};
    F -- Enriched Leads --> G{DB Layer (database.py/models.py)};
    G -- SQLAlchemy Async --> H[(SQL Database: PostgreSQL/SQLite)];
    I[config.py/.env] -- Settings --> B;
    I -- Settings --> C;
    I -- Settings --> F;
    I -- Settings --> G;
    K(Scheduler: APScheduler) -.-> B;
    L(API: FastAPI) -.-> G;
    L -.-> B;
    M(Alembic) <--> H;