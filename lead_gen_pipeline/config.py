# lead_gen_pipeline/config.py
# Version: Gemini-2025-05-26 22:05 EDT
import os
from pathlib import Path
from typing import List, Optional, Union

from pydantic import (
    HttpUrl,
    DirectoryPath,
    FilePath,
    field_validator,
    ValidationInfo,
    Field
)
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class CrawlerSettings(BaseSettings):
    """Settings specific to the crawler component."""
    model_config = SettingsConfigDict(env_prefix='CRAWLER_', extra='ignore', case_sensitive=False)

    USER_AGENTS: List[str] = Field(
        default=[
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
        ]
    )
    DEFAULT_TIMEOUT_SECONDS: int = Field(default=30, ge=5, le=120)
    MIN_DELAY_PER_DOMAIN_SECONDS: float = Field(default=3.0, ge=0.5)
    MAX_DELAY_PER_DOMAIN_SECONDS: float = Field(default=10.0, ge=1.0)
    MAX_RETRIES: int = Field(default=3, ge=0)
    BACKOFF_FACTOR: float = Field(default=0.8, ge=0.1) 
    USE_PLAYWRIGHT_BY_DEFAULT: bool = Field(default=False)
    PLAYWRIGHT_HEADLESS_MODE: bool = Field(default=True)
    HTTP_PROXY_URL: Optional[HttpUrl] = Field(default=None)
    HTTPS_PROXY_URL: Optional[HttpUrl] = Field(default=None)

    RESPECT_ROBOTS_TXT: bool = Field(default=True, description="Whether to fetch and respect robots.txt rules.")
    ROBOTS_TXT_USER_AGENT: str = Field(
        default="*",
        description="User agent string to use when checking robots.txt. '*' respects rules for all user agents."
    )
    ROBOTS_TXT_CACHE_SIZE: int = Field(default=100, ge=10, le=1000, description="Maximum number of compiled robots.txt parsers to keep in memory.")
    ROBOTS_TXT_FETCH_TIMEOUT_SECONDS: int = Field(default=10, ge=3, le=60, description="Timeout for fetching robots.txt files.")


    @field_validator('MAX_DELAY_PER_DOMAIN_SECONDS')
    @classmethod
    def max_delay_must_be_greater_than_min_delay(cls, v: float, info: ValidationInfo) -> float:
        if 'MIN_DELAY_PER_DOMAIN_SECONDS' in info.data and v < info.data['MIN_DELAY_PER_DOMAIN_SECONDS']:
            raise ValueError('MAX_DELAY_PER_DOMAIN_SECONDS must be >= MIN_DELAY_PER_DOMAIN_SECONDS')
        return v

class LoggingSettings(BaseSettings):
    """Settings for application logging."""
    model_config = SettingsConfigDict(env_prefix='LOGGING_', extra='ignore', case_sensitive=False)

    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE_PATH: Path = Field(default_factory=lambda: BASE_DIR / "logs" / "app.log")
    ERROR_LOG_FILE_PATH: Path = Field(default_factory=lambda: BASE_DIR / "logs" / "error.log")
    LOG_ROTATION_SIZE: str = Field(default="10 MB")
    LOG_RETENTION_POLICY: str = Field(default="7 days")

    @field_validator('LOG_FILE_PATH', 'ERROR_LOG_FILE_PATH', mode='before')
    @classmethod
    def ensure_log_dir_exists(cls, v: Union[str, Path], info: ValidationInfo) -> Path:
        log_path = Path(v)
        if not log_path.is_absolute():
            # Resolve relative to BASE_DIR if not absolute
            log_path = BASE_DIR / log_path
        
        # Ensure parent directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return log_path.resolve()

class DatabaseSettings(BaseSettings):
    """Settings for the database connection."""
    model_config = SettingsConfigDict(env_prefix='DATABASE_', extra='ignore', case_sensitive=False)

    DATABASE_URL: str = Field(default_factory=lambda: f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'leads_mvp.db'}")
    ECHO_SQL: bool = Field(default=False)

    @field_validator('DATABASE_URL', mode='before')
    @classmethod
    def ensure_db_dir_exists(cls, v: str, info: ValidationInfo) -> str:
        if v.startswith("sqlite") or v.startswith("sqlite+aiosqlite"):
            # Correctly handle "sqlite+aiosqlite:///relative/path/to/db.db"
            # or "sqlite:///absolute/path/to/db.db"
            
            uri_parts = v.split(":///", 1)
            if len(uri_parts) == 2:
                db_path_str = uri_parts[1]
                db_path = Path(db_path_str)
                
                if not db_path.is_absolute():
                    db_path = BASE_DIR / db_path
                
                db_path.parent.mkdir(parents=True, exist_ok=True)
                return f"{uri_parts[0]}:///{db_path.resolve()}"
            elif v.startswith("sqlite:///") and Path(v[10:]).is_absolute(): # For absolute paths like sqlite:////path/to/db
                 db_path = Path(v[10:])
                 db_path.parent.mkdir(parents=True, exist_ok=True)
                 return v # Already absolute and fine
                 
        return v # Return as is if not a local SQLite file path or format not recognized for dir creation

class AppSettings(BaseSettings):
    """Main application settings, composing other settings groups."""
    model_config = SettingsConfigDict(
        env_file=Path(os.getenv("ENV_FILE_PATH", BASE_DIR / ".env")),
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False,
        env_nested_delimiter='__'
    )

    PROJECT_NAME: str = Field(default="Lead Generation Pipeline") # Changed from B2B...
    BASE_DIR: DirectoryPath = Field(default=BASE_DIR)
    INPUT_URLS_CSV: FilePath = Field(default_factory=lambda: BASE_DIR / "data" / "urls_seed.csv")

    crawler: CrawlerSettings = CrawlerSettings()
    logging: LoggingSettings = LoggingSettings()
    database: DatabaseSettings = DatabaseSettings()

    MAX_PIPELINE_CONCURRENCY: int = Field(default=5, ge=1)
    MAX_CONCURRENT_REQUESTS_PER_DOMAIN: int = Field(default=1, ge=1)

try:
    settings = AppSettings()
except Exception as e:
    # Fallback to default settings in case of critical error during init.
    # This might happen if .env file is malformed or critical env vars are missing/invalid.
    # Logging might not be set up yet, so print to stderr.
    print(f"CRITICAL: Error loading application settings: {e}", file=os.sys.stderr)
    print("CRITICAL: Falling back to default settings. Check your .env file and configuration.", file=os.sys.stderr)
    settings = AppSettings(
        crawler=CrawlerSettings(),
        logging=LoggingSettings(), # Default logging settings will attempt to create log dirs
        database=DatabaseSettings(), # Default DB settings will attempt to create data dir
        _env_file=None # type: ignore [call-arg] # Prevent re-reading a potentially problematic .env
    )
