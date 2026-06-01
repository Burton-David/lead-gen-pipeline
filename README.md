# lead-gen-pipeline

Structured business-data extraction from web pages and Chamber of Commerce member
directories. Single pages are parsed deterministically; whole directories are navigated
and extracted by a **local LLM** (Qwen2-7B via llama.cpp) — no API keys, no data leaving
the machine.

The interesting part is the directory crawl: chamber sites bury member listings behind
wildly different layouts (category grids, A–Z indexes, paginated tables). Instead of a
bespoke parser per site, the pipeline asks a local model to find the directory and read
the listings, then repairs malformed model output and deduplicates the results before
they hit the database.

## What it does

- **Deterministic single-page extraction** — company name, phone numbers (E.164),
  emails (incl. obfuscated and Cloudflare-protected), postal addresses, social profiles,
  description, and canonical URL, using metadata, schema.org markup, and text heuristics.
- **Agentic directory navigation** — a local LLM locates member directories and extracts
  listings across varied layouts, with a **JSON-repair fallback** for malformed output.
- **Pluggable LLM backend** — ships with a llama.cpp Qwen2-7B backend; the `LLMBackend`
  protocol lets you swap in another model (or a fake, as the tests do).
- **Polite crawling** — honors `robots.txt`, rate-limits per domain, retries transient
  failures with backoff, and detects CAPTCHA challenge pages.
- **Bulk persistence** — deduplicating, batched upserts into SQLite with helper indexes.
- **Typed and tested** — SQLAlchemy 2.0 typed models; black + ruff + mypy clean; a
  deterministic test suite that runs without the model.

## Quickstart (no model required)

The single-page extractor needs only the core install:

```bash
git clone https://github.com/Burton-David/lead-gen-pipeline
cd lead-gen-pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

lead-gen test https://www.python.org
```

`lead-gen test <url>` fetches a page and prints the structured data it extracted — a
30-second way to see the parser work end to end.

Process a list of sites and store the results:

```bash
# data/urls_seed.csv has a `url` column
lead-gen run --input data/urls_seed.csv
lead-gen stats          # extraction coverage of the stored leads
lead-gen export -o leads.csv
```

## Chamber directories (local LLM)

The directory crawl needs the model and a headless browser:

```bash
pip install -e ".[llm,browser]"
playwright install chromium
lead-gen setup-llm                      # downloads Qwen2-7B-Instruct GGUF (~4 GB)

lead-gen chambers --url https://www.examplechamber.com
# or a CSV of chamber URLs:
lead-gen chambers --input data/chamber_urls.csv
```

Requirements for this path: ~8 GB RAM and ~4 GB disk for the model. Apple Silicon and
CUDA are used automatically when `llama-cpp-python` is built with the matching backend.

## Performance

Reproducible on any machine:

- **Bulk database throughput** — ~1,300 deduplicating upserts/second against SQLite on a
  laptop. Reproduce with `python scripts/benchmark_bulk_db.py 5000`.
- **Test suite** — 146 deterministic tests, ~64% line coverage, run in ~1.5s without the
  model (`pytest`).

From a development run against the Palo Alto Chamber directory (2025): ~296 businesses
across 26 categories in ~9 minutes, with high completeness on names and phone numbers and
lower completeness on emails and websites. These figures come from a single real run and
will vary by site, layout, and model build — treat them as illustrative, not a benchmark.

## How it works

```
chamber URL
   │  AsyncWebCrawler  (robots.txt, rate limiting, retries, Playwright for JS pages)
   ▼
HTML ──► LLMProcessor ──► find directory links ──► extract listings (JSON, repaired)
   │        (Qwen2-7B via pluggable LLMBackend)              │
   │                                                         ▼
   └────────────► HTMLScraper (chamber metadata)      deduplicate
                                                             │
                                                             ▼
                                            BulkDatabaseProcessor ──► SQLite ──► CSV
```

Core modules:

- `crawler.py` — async fetching, robots.txt, per-domain rate limiting, retries, CAPTCHA
  detection; HTTPX by default, Playwright/Chromium for JavaScript-rendered pages.
- `scraper.py` — deterministic single-page extraction; generic/placeholder noise is
  filtered via `generic_filters.py`.
- `llm_processor.py` — HTML→Markdown preprocessing, prompting, grammar-constrained JSON,
  and JSON-repair; reached through the `LLMBackend` protocol.
- `chamber_parser.py` / `chamber_pipeline.py` — directory discovery, pagination, dedup,
  and orchestration.
- `bulk_database.py` / `database.py` / `models.py` — typed SQLAlchemy 2.0 persistence.

## Responsible use

This tool reads **public** directory pages. It is built to be a polite, defensible
citizen, and you should keep it that way:

- **robots.txt is honored by default** (`CRAWLER__RESPECT_ROBOTS_TXT=true`). Disabling it
  is your responsibility.
- **Rate limiting** enforces a minimum delay per domain; keep concurrency modest.
- Respect each site's Terms of Service and applicable law. Don't collect personal data
  you don't have a lawful basis to process, and don't republish scraped data in ways the
  source prohibits.
- Identify yourself when a site asks: set a contact User-Agent via `CRAWLER__...` and
  reach out to operators if you intend sustained crawling.

Intended use is lawful B2B research and lead generation against directories that permit
it. It is not intended for bulk personal-data harvesting or for evading access controls.

## Configuration

Settings load from environment variables (and an optional `.env`), overriding the
built-in defaults. Nested groups use a `__` delimiter. See `.env.example`; common keys:

```bash
DATABASE__DATABASE_URL="sqlite+aiosqlite:///./data/leads.db"
CRAWLER__RESPECT_ROBOTS_TXT=true
CRAWLER__MIN_DELAY_PER_DOMAIN_SECONDS=3.0
CRAWLER__USE_PLAYWRIGHT_BY_DEFAULT=false
LLM__MODEL_PATH="./models/qwen2-7b-instruct-q4_k_m.gguf"
LLM__CONTEXT_SIZE=32768
```

`lead-gen config` prints the active configuration.

## Development

```bash
pip install -e ".[dev]"
black --check . && ruff check . && mypy lead_gen_pipeline && pytest
```

The default test run excludes the model. The live-model check is marked and opt-in:

```bash
pytest -m live_llm           # requires the downloaded GGUF model
python scripts/smoke_llm.py  # one-off manual check
```

Optional extras: `llm` (llama-cpp-python + huggingface-hub), `browser` (Playwright),
`nlp` (spaCy NER fallback for company names), `dev` (toolchain).

## Limits

- Extraction quality on the LLM path depends on the model build and the site; very
  JavaScript-heavy or aggressively bot-protected directories may extract poorly.
- The default store is SQLite, which is plenty for single-machine runs; swap
  `DATABASE__DATABASE_URL` for Postgres for larger deployments.
- spaCy-based company-name extraction is an optional fallback and off by default.

## License

MIT — see [LICENSE](LICENSE).
