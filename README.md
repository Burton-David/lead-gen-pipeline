# Chamber Business Directory Scraper

Python tool for extracting business data from Chamber of Commerce member directories using local LLM integration.

After manually collecting business contacts from chamber websites for consulting projects, I built this to automate the process. Uses Qwen2-7B locally to intelligently navigate different directory structures and extract structured business data.

## Features

- **Adaptive navigation**: Handles category-based, alphabetical, and paginated directory layouts
- **Structured extraction**: Business names, websites, phone numbers, emails, addresses, industries
- **Local LLM**: No API costs, complete data privacy, works offline
- **Production ready**: Bulk database operations, deduplication, CSV export
- **Robust parsing**: JSON repair fallbacks handle malformed LLM output

## Quick Start

```bash
git clone https://github.com/Burton-David/lead-gen-pipeline
cd lead-gen-pipeline
./setup.sh

# Extract from single chamber
python cli.py chambers --url https://www.paloaltochamber.com

# Export results
python cli.py export --output leads.csv
```

## Performance

- **Palo Alto Chamber**: 296 businesses from 26 categories in 9 minutes
- **Data completeness**: 100% names/phones, 90% emails, 85% websites
- **Database throughput**: 500+ records/second bulk operations
- **Memory usage**: 4-8GB with LLM loaded

## Installation

**Requirements:**
- Python 3.8+
- 8GB+ RAM (for local LLM)
- ~4GB disk space (model download)

**Setup:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python cli.py init
```

The setup script downloads Qwen2-7B (~4GB) automatically.

## Usage Examples

**Single chamber:**
```bash
python cli.py chambers --url https://business.yourchamber.com
```

**Multiple chambers:**
```csv
# chambers.csv
url
https://business.chamber1.com
https://business.chamber2.com
```

```bash
python cli.py chambers --input chambers.csv
```

**View results:**
```bash
python cli.py stats    # Extraction statistics
python cli.py export   # Export to CSV
```

## How It Works

1. **LLM Analysis**: Qwen2-7B analyzes chamber page structure and identifies directory sections
2. **Pattern Recognition**: Handles different layouts (categories, alphabetical, pagination) automatically  
3. **Data Extraction**: Extracts structured business information with validation
4. **Deduplication**: Removes duplicates based on website/name combinations

## Architecture

```
Chamber URL → LLM Navigation → Data Extraction → Validation → SQLite Database
     ↓              ↓              ↓           ↓           ↓
HTML Content   Directory Links   Business Data  Clean Data  Exportable CSV
```

**Core modules:**
- `llm_processor.py` - Qwen2-7B integration for page analysis
- `chamber_parser.py` - Directory navigation and pagination  
- `crawler.py` - Web scraping with rate limiting, browser automation
- `bulk_database.py` - Efficient database operations

## Database Schema

```sql
CREATE TABLE leads (
    id INTEGER PRIMARY KEY,
    company_name VARCHAR,
    website VARCHAR,
    phone_numbers JSON,    -- ["555-1234", "555-5678"]
    emails JSON,           -- ["info@company.com"]
    addresses JSON,        -- ["123 Main St, City, State"]
    industry_tags JSON,    -- ["Technology", "Consulting"]
    chamber_name VARCHAR,
    chamber_url VARCHAR,
    created_at TIMESTAMP
);
```

## Configuration

Key settings in `.env`:
```bash
DATABASE_URL="sqlite+aiosqlite:///./data/leads.db"
MAX_CONCURRENCY=5
CRAWLER_TIMEOUT_SECONDS=30
LLM_MODEL_PATH="./models/qwen2-7b-instruct-q4_k_m.gguf"
```

## Troubleshooting

**"llama-cpp-python not available"**
```bash
pip uninstall llama-cpp-python
# For Apple Silicon:
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python --no-cache-dir
# For Intel/AMD:
CMAKE_ARGS="-DLLAMA_BLAS=ON" pip install llama-cpp-python --no-cache-dir
```

**Model download fails:**
```bash
python cli.py setup-llm
```

**Low extraction rates:**
Some chambers use heavy JavaScript. System falls back to traditional scraping automatically.

## Extending the System

The LLM processor can adapt to other directory types:
- Industry association member lists
- Professional organization directories  
- Business listing websites
- Government contractor databases

For custom adaptations or consulting on B2B data extraction projects, contact me at [databurton.com](https://databurton.com).

## Contributing

Pull requests welcome. The prompt engineering can always be refined - LLMs occasionally miss businesses or extract incomplete data.

**Development setup:**
```bash
git clone https://github.com/Burton-David/lead-gen-pipeline
cd lead-gen-pipeline
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

## License

MIT License - see LICENSE file.

---

**Built for B2B lead generation and business intelligence applications.**

*For custom business directory extraction or B2B data projects, reach out via [databurton.com](https://databurton.com)*
