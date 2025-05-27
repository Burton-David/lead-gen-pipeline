# create_handoff_doc.py
# Version: 2025-05-26 14:20 EDT (Ensuring clean provision)
import os
from pathlib import Path
import time 

# --- Configuration: Define file paths relative to the script's location (project root) ---
PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_FILENAME = PROJECT_ROOT / "PROJECT_HANDOFF_DOCUMENT.md"

# Files to include in the handoff document, in desired order
# The script will read these files from your local project directory.
FILES_TO_INCLUDE = {
    "DEV_DOCUMENTATION.md": "4. Developer Documentation (`DEV_DOCUMENTATION.md`)",
    "lead_gen_pipeline/config.py": "5.1. `lead_gen_pipeline/config.py`",
    "tests/unit/test_config.py": "5.2. `tests/unit/test_config.py`",
    "lead_gen_pipeline/utils.py": "5.3. `lead_gen_pipeline/utils.py`",
    "tests/unit/test_utils.py": "5.4. `tests/unit/test_utils.py`",
    "lead_gen_pipeline/crawler.py": "5.5. `lead_gen_pipeline/crawler.py`",
    "tests/unit/test_crawler.py": "5.6. `tests/unit/test_crawler.py`",
    "lead_gen_pipeline/scraper.py": "5.7. `lead_gen_pipeline/scraper.py`",
    "tests/unit/test_scraper.py": "5.8. `tests/unit/test_scraper.py`",
    "requirements.txt": "5.9. `requirements.txt`",
}

# This section now contains the full original prompt you provided.
ORIGINAL_PROJECT_REQUIREMENTS = """
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
"""

COLLABORATION_METHODS = """
* Work step-by-step: AI provides code/instructions for one specific task, user executes and provides full terminal output for debugging.
* Terminal output is the source of truth for debugging.
* Code provided in complete, runnable blocks (Canvases/Immersive Documents).
* Version comments (e.g., `# Version: Gemini-YYYY-MM-DD HH:MM UTC`) at the top of Python files provided by the AI.
* Keep `DEV_DOCUMENTATION.md` updated with each completed feature.
* Focus on robust, well-tested, production-quality code.
* Prioritize ethical crawling, with advanced stealth as a later enhancement.
* User manages local files and Git repository. AI provides code and guidance.
"""

DIRECTORY_TREE = """
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
"""

# This prompt reflects the current state (scraper basics done, moving to models/DB)
PROMPT_FOR_NEW_SESSION = """
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
"""

def get_file_content(filepath: Path) -> str:
    """Reads and returns the content of a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"!!! File not found: {filepath}. Please ensure this script is in the project root and the file exists. !!!"
    except Exception as e:
        return f"!!! Error reading file {filepath}: {e} !!!"

def main():
    content_parts = []

    # --- Header ---
    content_parts.append("# Lead Generation Pipeline - Project Handoff")
    content_parts.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n")

    # --- Prompt for New Session ---
    content_parts.append("## Prompt for New Gemini Session (to accompany this document)")
    content_parts.append("```text")
    content_parts.append(PROMPT_FOR_NEW_SESSION.strip())
    content_parts.append("```\n")

    # --- Original Requirements ---
    content_parts.append("## 1. Original Project Requirements & Goal")
    content_parts.append(ORIGINAL_PROJECT_REQUIREMENTS.strip() + "\n")

    # --- Collaboration Methods ---
    content_parts.append("## 2. Effective Collaboration Methods Summary")
    content_parts.append(COLLABORATION_METHODS.strip() + "\n")

    # --- Directory Tree ---
    content_parts.append("## 3. Project Directory Tree")
    content_parts.append("```")
    content_parts.append(DIRECTORY_TREE.strip())
    content_parts.append("```\n")
    
    dev_docs_key = "DEV_DOCUMENTATION.md"
    dev_docs_title_template = FILES_TO_INCLUDE.get(dev_docs_key) 

    if dev_docs_title_template:
        # Files for section 5 should not include Dev Docs
        files_for_section_5 = {k: v for k, v in FILES_TO_INCLUDE.items() if k != dev_docs_key}
        
        # Format title for section 4 (Dev Docs)
        section_4_title_parts = dev_docs_title_template.split('.', 1)
        section_4_title = f"## {section_4_title_parts[0].strip()}. {section_4_title_parts[1].strip()}"
        content_parts.append(section_4_title)
        content_parts.append("\n---\n") # Markdown horizontal rule
        content_parts.append(get_file_content(PROJECT_ROOT / dev_docs_key))
        content_parts.append("\n---\n") # Markdown horizontal rule
    else:
        content_parts.append("## 4. Developer Documentation (`DEV_DOCUMENTATION.md`)")
        content_parts.append("!!! DEV_DOCUMENTATION.md entry not found in FILES_TO_INCLUDE or path is incorrect. Please check the `FILES_TO_INCLUDE` dictionary in this script. !!!\n")

    content_parts.append("## 5. Current Python Code Files & Other Key Files\n")

    current_minor_section = 1
    # Sort files based on the minor number in their title template (e.g., "5.1", "5.2")
    # This ensures they appear in the order defined in FILES_TO_INCLUDE for section 5
    sorted_file_items = sorted(
        files_for_section_5.items(), # Use the filtered dict
        key=lambda item: float(item[1].split('.')[1]) if '.' in item[1] else float('inf')
    )

    for rel_path_str, original_title_template in sorted_file_items:
        file_path = PROJECT_ROOT / rel_path_str
        
        # Reconstruct title to ensure continuous numbering under section 5
        # Example: "5.1. `lead_gen_pipeline/config.py`"
        # Extract the filename part like `lead_gen_pipeline/config.py`
        filename_part_match = re.search(r'`(.*?)`', original_title_template)
        filename_display = filename_part_match.group(1) if filename_part_match else rel_path_str
        
        content_parts.append(f"### 5.{current_minor_section}. `{filename_display}`")
        
        file_extension = file_path.suffix.lstrip('.')
        code_block_lang = "python" if file_extension == "py" else file_extension
        if not code_block_lang: 
            code_block_lang = "text" # For files like .gitignore or requirements.txt if suffix is empty

        content_parts.append(f"```{code_block_lang}")
        content_parts.append(get_file_content(file_path))
        content_parts.append("```\n")
        current_minor_section += 1

    # Placeholders for __init__.py and Other Files
    next_placeholder_minor_section = current_minor_section
    content_parts.append(f"### 5.{next_placeholder_minor_section}. `lead_gen_pipeline/__init__.py`")
    content_parts.append("```python")
    content_parts.append("# This file is currently empty, serving only to mark the directory as a package.")
    content_parts.append("```\n")

    next_placeholder_minor_section += 1
    content_parts.append(f"### 5.{next_placeholder_minor_section}. Other Files")
    content_parts.append("The following files also exist and are part of the project setup:")
    content_parts.append("- `.env` (local, ignored by Git - contains secrets/local overrides)")
    content_parts.append("- `.env.example` (template for `.env`)")
    content_parts.append("- `.gitignore` (standard Python .gitignore)")
    content_parts.append("- `README.md` (project README, can be simple for now)")
    content_parts.append("- `LICENSE` (e.g., MIT License)")
    content_parts.append("- `cli_mvp.py` (placeholder, empty)")
    content_parts.append("- `run_pipeline_mvp.py` (placeholder, empty)")
    content_parts.append("- `data/urls_seed.csv` (placeholder, empty or with example URLs)")
    content_parts.append("- `logs/app.log` (will be created by logger)")
    content_parts.append("- `tests/__init__.py`, `tests/integration/__init__.py`, `tests/unit/__init__.py` (empty package markers)\n")

    # --- Assemble and Write ---
    final_markdown = "\n".join(content_parts)
    try:
        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
            f.write(final_markdown)
        print(f"Successfully generated handoff document: {OUTPUT_FILENAME}")
    except Exception as e:
        print(f"Error writing handoff document: {e}")

if __name__ == "__main__":
    import re # Ensure re is imported for the main function if not already
    main()