# Full image including the local-LLM and browser extras for chamber processing.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build tools (for llama-cpp-python) and Playwright/Chromium system libraries.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git \
    libnss3 libnspr4 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxrandr2 libgbm1 libxss1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash app
WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml README.md ./
COPY lead_gen_pipeline ./lead_gen_pipeline
RUN pip install ".[llm,browser]" && playwright install --with-deps chromium

# Application data and remaining files.
COPY . .
RUN mkdir -p /app/data /app/logs /app/models && chown -R app:app /app
USER app

VOLUME ["/app/data", "/app/logs", "/app/models"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD lead-gen config || exit 1

# Default to showing CLI help; docker-compose overrides this with a real command.
CMD ["lead-gen", "--help"]
