"""Application configuration.

Settings are layered: process environment variables override values from a `.env`
file, which override the defaults declared here. Nested groups use a `__` delimiter
(for example ``CRAWLER__DEFAULT_TIMEOUT_SECONDS``), while each group also accepts its
own flat prefix (``CRAWLER_...``, ``LLM_...``) for convenience.
"""

import sys
from pathlib import Path

from pydantic import (
    DirectoryPath,
    Field,
    FilePath,
    HttpUrl,
    ValidationInfo,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class CrawlerSettings(BaseSettings):
    """Settings specific to the crawler component."""

    model_config = SettingsConfigDict(
        env_prefix="CRAWLER_", extra="ignore", case_sensitive=False
    )

    USER_AGENTS: list[str] = Field(
        default=[
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) "
            "Gecko/20100101 Firefox/126.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) "
            "Gecko/20100101 Firefox/126.0",
        ]
    )
    DEFAULT_TIMEOUT_SECONDS: int = Field(default=30, ge=5, le=120)
    MIN_DELAY_PER_DOMAIN_SECONDS: float = Field(default=3.0, ge=0.5)
    MAX_DELAY_PER_DOMAIN_SECONDS: float = Field(default=10.0, ge=1.0)
    MAX_RETRIES: int = Field(default=3, ge=0)
    BACKOFF_FACTOR: float = Field(default=0.8, ge=0.1)
    USE_PLAYWRIGHT_BY_DEFAULT: bool = Field(default=False)
    PLAYWRIGHT_HEADLESS_MODE: bool = Field(default=True)
    HTTP_PROXY_URL: HttpUrl | None = Field(default=None)
    HTTPS_PROXY_URL: HttpUrl | None = Field(default=None)

    RESPECT_ROBOTS_TXT: bool = Field(
        default=True, description="Whether to fetch and respect robots.txt rules."
    )
    ROBOTS_TXT_USER_AGENT: str = Field(
        default="*",
        description="User agent used when checking robots.txt ('*' = all agents).",
    )
    ROBOTS_TXT_CACHE_SIZE: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Maximum number of compiled robots.txt parsers to keep in memory.",
    )
    ROBOTS_TXT_FETCH_TIMEOUT_SECONDS: int = Field(
        default=10, ge=3, le=60, description="Timeout for fetching robots.txt files."
    )

    @field_validator("MAX_DELAY_PER_DOMAIN_SECONDS")
    @classmethod
    def max_delay_must_be_greater_than_min_delay(
        cls, v: float, info: ValidationInfo
    ) -> float:
        min_delay = info.data.get("MIN_DELAY_PER_DOMAIN_SECONDS")
        if min_delay is not None and v < min_delay:
            raise ValueError(
                "MAX_DELAY_PER_DOMAIN_SECONDS must be >= MIN_DELAY_PER_DOMAIN_SECONDS"
            )
        return v


class LLMSettings(BaseSettings):
    """Settings for the local LLM used in chamber-directory processing.

    These mirror the parameters consumed by the llama.cpp backend. They are read by
    :class:`~lead_gen_pipeline.llm_processor.LLMProcessor` so the model can be tuned
    without code changes.
    """

    model_config = SettingsConfigDict(
        env_prefix="LLM_", extra="ignore", case_sensitive=False
    )

    MODEL_PATH: Path = Field(
        default_factory=lambda: BASE_DIR / "models" / "qwen2-7b-instruct-q4_k_m.gguf",
        description="Path to the GGUF model file.",
    )
    CONTEXT_SIZE: int = Field(default=32768, ge=512)
    MAX_TOKENS: int = Field(default=4096, ge=64)
    TEMPERATURE: float = Field(default=0.0, ge=0.0, le=2.0)
    N_GPU_LAYERS: int = Field(
        default=-1, description="GPU layers to offload; -1 offloads all available."
    )
    SEED: int = Field(default=42)
    HTML_CACHE_SIZE: int = Field(default=100, ge=1)


class LoggingSettings(BaseSettings):
    """Settings for application logging."""

    model_config = SettingsConfigDict(
        env_prefix="LOGGING_", extra="ignore", case_sensitive=False
    )

    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE_PATH: Path = Field(default_factory=lambda: BASE_DIR / "logs" / "app.log")
    ERROR_LOG_FILE_PATH: Path = Field(
        default_factory=lambda: BASE_DIR / "logs" / "error.log"
    )
    LOG_ROTATION_SIZE: str = Field(default="10 MB")
    LOG_RETENTION_POLICY: str = Field(default="7 days")

    @field_validator("LOG_FILE_PATH", "ERROR_LOG_FILE_PATH", mode="before")
    @classmethod
    def ensure_log_dir_exists(cls, v: str | Path, info: ValidationInfo) -> Path:
        log_path = Path(v)
        if not log_path.is_absolute():
            log_path = BASE_DIR / log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return log_path.resolve()


class DatabaseSettings(BaseSettings):
    """Settings for the database connection."""

    model_config = SettingsConfigDict(
        env_prefix="DATABASE_", extra="ignore", case_sensitive=False
    )

    DATABASE_URL: str = Field(
        default_factory=lambda: (
            f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'leads_mvp.db'}"
        )
    )
    ECHO_SQL: bool = Field(default=False)

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def ensure_db_dir_exists(cls, v: str, info: ValidationInfo) -> str:
        if v.startswith("sqlite"):
            # Handles "sqlite+aiosqlite:///relative/path.db" and
            # "sqlite:///absolute/path.db" alike by resolving the path component.
            uri_parts = v.split(":///", 1)
            if len(uri_parts) == 2:
                db_path = Path(uri_parts[1])
                if not db_path.is_absolute():
                    db_path = BASE_DIR / db_path
                db_path.parent.mkdir(parents=True, exist_ok=True)
                return f"{uri_parts[0]}:///{db_path.resolve()}"
        return v


class AppSettings(BaseSettings):
    """Main application settings, composing the per-component groups."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_nested_delimiter="__",
    )

    PROJECT_NAME: str = Field(default="Lead Generation Pipeline")
    BASE_DIR: DirectoryPath = Field(default=BASE_DIR)
    INPUT_URLS_CSV: FilePath = Field(
        default_factory=lambda: BASE_DIR / "data" / "urls_seed.csv"
    )

    crawler: CrawlerSettings = Field(default_factory=CrawlerSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)

    MAX_PIPELINE_CONCURRENCY: int = Field(default=5, ge=1)
    MAX_CONCURRENT_REQUESTS_PER_DOMAIN: int = Field(default=1, ge=1)


try:
    settings = AppSettings()
except Exception as e:  # pragma: no cover - defensive bootstrap path
    # If the .env file is malformed, fall back to defaults rather than crashing on
    # import. Logging is not configured this early, so report to stderr.
    print(f"CRITICAL: Error loading application settings: {e}", file=sys.stderr)
    print(
        "CRITICAL: Falling back to default settings. Check your .env file.",
        file=sys.stderr,
    )
    settings = AppSettings(_env_file=None)  # type: ignore[call-arg]
