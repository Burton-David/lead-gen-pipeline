# Architecture Documentation

## System Overview

The B2B Intelligence Platform is designed as a modular, scalable system for extracting business data from web sources. The architecture separates concerns into distinct layers while maintaining high performance and reliability.

## Core Architecture

### Layer 1: Data Collection Engine

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│   LLM Processor  │───▶│  Web Crawler    │
│                 │    │   (Qwen2 7B)     │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Chamber URLs    │    │ AI Navigation    │    │ HTTP/Browser    │
│ Business URLs   │    │ Directory Parse  │    │ Automation      │
│ Industry Lists  │    │ Pagination       │    │ JS Rendering    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Layer 2: Data Processing Pipeline

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  HTML Scraper   │───▶│ Data Processor   │───▶│ Bulk Database   │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ BeautifulSoup   │    │ Normalize        │    │ SQLite/Postgres │
│ Phone/Email     │    │ Deduplicate      │    │ Batch Insert    │
│ Address Extract │    │ Validate         │    │ Performance     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Layer 3: Application Interface

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Tools     │───▶│   Pipeline       │───▶│   Export        │
│                 │    │   Orchestrator   │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Commands        │    │ Job Management   │    │ CSV/JSON        │
│ Configuration   │    │ Progress Track   │    │ Database        │
│ Statistics      │    │ Error Handling   │    │ Integration     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Component Details

### LLM Processor (`llm_processor.py`)

**Purpose**: Intelligent web navigation and content extraction using large language models.

**Key Features**:
- Qwen2 Instruct 7B model integration
- HTML-to-Markdown preprocessing for token efficiency
- JSON-structured output with grammar enforcement
- Smart caching for repeated content processing

**Technical Implementation**:
- Uses llama-cpp-python for local model execution
- 32K context window for processing large web pages
- 4-bit quantization for memory efficiency (~6GB VRAM)
- Async/await pattern for non-blocking execution

### Chamber Parser (`chamber_parser.py`)

**Purpose**: Orchestrates the complete chamber directory processing workflow.

**Key Features**:
- Multi-stage processing (discovery → navigation → extraction)
- Pagination handling with cycle detection
- Concurrent processing with rate limiting
- Comprehensive error recovery and retry logic

**Processing Flow**:
1. Chamber info extraction from main page
2. LLM-powered directory link discovery
3. Business listing extraction with pagination
4. Data deduplication and normalization

### Web Crawler (`crawler.py`)

**Purpose**: High-performance web content fetching with respectful crawling practices.

**Key Features**:
- Dual-mode operation (HTTPX for speed, Playwright for JS)
- robots.txt compliance with intelligent caching
- Rate limiting and domain-specific delays
- User-agent rotation and proxy support

**Performance Characteristics**:
- Async architecture for high concurrency
- Connection pooling and keep-alive optimization
- Adaptive retry logic with exponential backoff
- Memory-efficient content streaming

### HTML Scraper (`scraper.py`)

**Purpose**: Structured data extraction from HTML content.

**Key Features**:
- Multi-strategy company name extraction
- Phone number parsing with international support
- Email deobfuscation (Cloudflare protection, etc.)
- Social media profile link validation
- Address extraction with postal pattern matching

**Extraction Strategies**:
- Schema.org markup processing
- OpenGraph meta tag analysis
- NLP-based entity recognition (optional)
- Heuristic pattern matching

### Bulk Database (`bulk_database.py`)

**Purpose**: High-performance database operations optimized for large-scale data insertion.

**Key Features**:
- Batch processing with configurable batch sizes
- Hash-based deduplication to prevent duplicates
- Database-specific optimization (SQLite pragmas, PostgreSQL UPSERT)
- Performance monitoring and statistics collection

**Scalability Features**:
- Async database operations
- Index optimization for common queries
- Memory-efficient processing of large datasets
- Configurable concurrency limits

## Data Flow Architecture

### 1. Input Processing

```python
# Chamber URLs loaded from CSV or provided directly
chamber_urls = load_chamber_urls("data/chamber_urls.csv")

# Parallel processing with concurrency control
semaphore = asyncio.Semaphore(max_concurrent_chambers)
```

### 2. LLM-Powered Navigation

```python
# HTML preprocessing for efficient token usage
markdown_content = html_to_markdown(html_content)

# LLM analyzes page structure and identifies business directory links
directory_links = await llm_processor.find_directory_links(markdown_content)

# LLM extracts business listings with structured output
businesses = await llm_processor.extract_business_listings(directory_content)
```

### 3. Data Processing Pipeline

```python
# Normalize business data
normalized_businesses = normalize_business_data(raw_businesses, chamber_info)

# Bulk database insertion with deduplication
stats = await bulk_processor.bulk_insert_businesses(normalized_businesses)
```

## Performance Characteristics

### Throughput Benchmarks

- **Chamber Processing**: 20-50 chambers per hour
- **Business Extraction**: 100-2000 businesses per chamber
- **Database Operations**: 500+ records/second bulk insert
- **LLM Processing**: 20-50 tokens/second (depends on hardware)

### Resource Requirements

- **Memory**: 8GB minimum, 16GB recommended
- **Storage**: 100GB+ for national-scale processing
- **CPU**: 4+ cores, benefits from 8+ cores
- **GPU**: Optional, accelerates LLM processing

### Scalability Limits

- **SQLite**: Up to ~10 million records efficiently
- **PostgreSQL**: Scales to billions of records
- **Concurrent Processing**: Limited by memory and LLM capacity
- **Network**: Respectful crawling limits throughput

## Security Architecture

### Data Privacy

- Only processes publicly available business information
- No storage of sensitive personal data
- Respects robots.txt and crawling etiquette
- Configurable rate limiting and delays

### Code Security

- Input validation for all external data
- Secure handling of configuration and credentials
- No hardcoded secrets or API keys
- Containerized deployment for isolation

## Deployment Architectures

### Single Machine Deployment

```yaml
# docker-compose.yml
services:
  b2b-intelligence:
    build: .
    volumes:
      - ./data:/app/data
      - ./models:/app/models
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///data/business_data.db
```

### Distributed Deployment (Future)

```yaml
# Kubernetes deployment for scale
apiVersion: apps/v1
kind: Deployment
metadata:
  name: b2b-intelligence
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: processor
        resources:
          requests:
            memory: "8Gi"
            cpu: "4"
```

## Monitoring and Observability

### Built-in Metrics

- Processing rates (chambers/hour, businesses/hour)
- Success/failure rates by data source
- Database performance statistics
- Memory and CPU utilization tracking

### Logging Architecture

- Structured logging with configurable levels
- Separate error logs for debugging
- Performance metrics logging
- Audit trail for all data processing

### Health Checks

- LLM model initialization status
- Database connectivity and performance
- External dependency health (web crawling)
- Resource utilization monitoring

## Extension Points

### Adding New Data Sources

1. Implement source-specific parser
2. Integrate with existing pipeline orchestrator
3. Add configuration for source-specific settings
4. Update database schema if needed

### Custom LLM Models

1. Implement model adapter interface
2. Add model-specific configuration
3. Update prompt templates as needed
4. Test with existing validation suite

### Additional Export Formats

1. Implement exporter interface
2. Add format-specific serialization
3. Update CLI command options
4. Add validation for new format

This architecture provides a solid foundation for the current B2B Intelligence Platform while maintaining flexibility for future enhancements and scale requirements.
