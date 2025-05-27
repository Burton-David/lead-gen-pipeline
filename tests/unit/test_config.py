# tests/unit/test_config.py
# Version: 2025-05-23 16:30 EDT
import os
import pytest
from pathlib import Path
import sys

PROJECT_ROOT_FOR_IMPORTS = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORTS))

from pydantic import ValidationError
from lead_gen_pipeline.config import AppSettings, CrawlerSettings, LoggingSettings, DatabaseSettings

TEST_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

@pytest.fixture(scope="function")
def temp_env_vars_for_override(monkeypatch):
    """Fixture to temporarily set OS environment variables for override tests."""
    env_vars_to_set = {
        "PROJECT_NAME": "Test Project From OS Env Override",
        "LOGGING__LOG_LEVEL": "DEBUG",
        "DATABASE__DATABASE_URL": f"sqlite+aiosqlite:///{TEST_PROJECT_ROOT / 'db_from_os_env_override.db'}",
        "CRAWLER__DEFAULT_TIMEOUT_SECONDS": "50",
        "CRAWLER__RESPECT_ROBOTS_TXT": "false", # Test boolean override
        "CRAWLER__ROBOTS_TXT_USER_AGENT": "TestBot/1.0",
        "CRAWLER__ROBOTS_TXT_CACHE_SIZE": "50",
        "CRAWLER__ROBOTS_TXT_FETCH_TIMEOUT_SECONDS": "5",
        "MAX_PIPELINE_CONCURRENCY": "15"
    }
    for k, v in env_vars_to_set.items():
        monkeypatch.setenv(k, str(v))
    yield env_vars_to_set
    # No need to cleanup, monkeypatch handles it

@pytest.fixture(scope="function")
def temp_dot_env_file_for_override(tmp_path):
    """Fixture to create a temporary .env file for override testing."""
    env_content = f"""
PROJECT_NAME="Project From Temp DotEnv File Override"
LOGGING__LOG_LEVEL="WARNING"
DATABASE__DATABASE_URL="sqlite+aiosqlite:///{tmp_path}/db_from_temp_dotenv_override.db"
CRAWLER__DEFAULT_TIMEOUT_SECONDS="55"
CRAWLER__RESPECT_ROBOTS_TXT=true
CRAWLER__ROBOTS_TXT_USER_AGENT="DotEnvBot/2.0"
CRAWLER__ROBOTS_TXT_CACHE_SIZE="150"
CRAWLER__ROBOTS_TXT_FETCH_TIMEOUT_SECONDS="15"
MAX_PIPELINE_CONCURRENCY="18"
INPUT_URLS_CSV="{tmp_path}/custom_urls.csv"
    """
    dot_env_path = tmp_path / ".env.test_override"
    dot_env_path.write_text(env_content)
    (tmp_path / "custom_urls.csv").touch()
    return dot_env_path

def test_default_settings_load_correctly():
    """Test that AppSettings loads with default values when no .env or OS env vars affect it."""
    settings = AppSettings(_env_file=None) # type: ignore [call-arg]

    assert settings.PROJECT_NAME == "B2B Lead Generation Pipeline"
    assert settings.BASE_DIR == TEST_PROJECT_ROOT
    assert settings.INPUT_URLS_CSV.resolve() == (TEST_PROJECT_ROOT / "data" / "urls_seed.csv").resolve()
    
    assert settings.logging.LOG_LEVEL == "INFO"
    assert settings.logging.LOG_FILE_PATH.resolve() == (TEST_PROJECT_ROOT / "logs" / "app.log").resolve()
    assert settings.logging.LOG_FILE_PATH.parent.exists()

    # Crawler default settings
    assert settings.crawler.DEFAULT_TIMEOUT_SECONDS == 30
    assert settings.crawler.HTTP_PROXY_URL is None
    assert settings.crawler.RESPECT_ROBOTS_TXT is True # Default is True
    assert settings.crawler.ROBOTS_TXT_USER_AGENT == "*" # Default is "*"
    assert settings.crawler.ROBOTS_TXT_CACHE_SIZE == 100
    assert settings.crawler.ROBOTS_TXT_FETCH_TIMEOUT_SECONDS == 10


    expected_db_path = (TEST_PROJECT_ROOT / "data" / "leads_mvp.db").resolve()
    assert settings.database.DATABASE_URL == f"sqlite+aiosqlite:///{expected_db_path}"
    assert Path(expected_db_path).parent.exists()
    assert settings.database.ECHO_SQL is False
    assert settings.MAX_PIPELINE_CONCURRENCY == 5

def test_settings_override_with_env_variables(temp_env_vars_for_override):
    """Test that settings can be overridden by OS environment variables."""
    current_settings = AppSettings(_env_file=None) # type: ignore [call-arg] # Ignore any actual .env file

    assert current_settings.PROJECT_NAME == "Test Project From OS Env Override"
    assert current_settings.logging.LOG_LEVEL == "DEBUG"
    assert current_settings.crawler.DEFAULT_TIMEOUT_SECONDS == 50
    
    # Test new crawler settings override
    assert current_settings.crawler.RESPECT_ROBOTS_TXT is False # 'false' string becomes False boolean
    assert current_settings.crawler.ROBOTS_TXT_USER_AGENT == "TestBot/1.0"
    assert current_settings.crawler.ROBOTS_TXT_CACHE_SIZE == 50
    assert current_settings.crawler.ROBOTS_TXT_FETCH_TIMEOUT_SECONDS == 5


    expected_db_path = (TEST_PROJECT_ROOT / "db_from_os_env_override.db").resolve()
    assert current_settings.database.DATABASE_URL == f"sqlite+aiosqlite:///{expected_db_path}"
    assert Path(expected_db_path).parent.exists()
    assert current_settings.MAX_PIPELINE_CONCURRENCY == 15

def test_settings_override_with_dotenv_file(temp_dot_env_file_for_override):
    """Test that settings can be overridden by a specific .env file."""
    current_settings = AppSettings(_env_file=temp_dot_env_file_for_override)

    assert current_settings.PROJECT_NAME == "Project From Temp DotEnv File Override"
    assert current_settings.logging.LOG_LEVEL == "WARNING"
    expected_db_path_dotenv = (temp_dot_env_file_for_override.parent / "db_from_temp_dotenv_override.db").resolve()
    assert current_settings.database.DATABASE_URL == f"sqlite+aiosqlite:///{expected_db_path_dotenv}"
    assert Path(expected_db_path_dotenv).parent.exists()
    assert current_settings.crawler.DEFAULT_TIMEOUT_SECONDS == 55
    
    # Test new crawler settings override from .env file
    assert current_settings.crawler.RESPECT_ROBOTS_TXT is True # 'true' string becomes True
    assert current_settings.crawler.ROBOTS_TXT_USER_AGENT == "DotEnvBot/2.0"
    assert current_settings.crawler.ROBOTS_TXT_CACHE_SIZE == 150
    assert current_settings.crawler.ROBOTS_TXT_FETCH_TIMEOUT_SECONDS == 15

    assert current_settings.MAX_PIPELINE_CONCURRENCY == 18
    expected_csv_path = (temp_dot_env_file_for_override.parent / "custom_urls.csv").resolve()
    assert current_settings.INPUT_URLS_CSV.resolve() == expected_csv_path

def test_crawler_delay_validation():
    """Test validation for crawler min/max delay."""
    with pytest.raises(ValueError, match="MAX_DELAY_PER_DOMAIN_SECONDS must be >= MIN_DELAY_PER_DOMAIN_SECONDS"):
        CrawlerSettings(MIN_DELAY_PER_DOMAIN_SECONDS=5.0, MAX_DELAY_PER_DOMAIN_SECONDS=2.0)
    try:
        CrawlerSettings(MIN_DELAY_PER_DOMAIN_SECONDS=2.0, MAX_DELAY_PER_DOMAIN_SECONDS=5.0)
    except ValueError:
        pytest.fail("Valid delay settings raised ValueError")

def test_log_path_creation(tmp_path, monkeypatch):
    """Test that log directories are created when settings are loaded with custom paths from .env."""
    dot_env_path = tmp_path / ".env.logtest"
    relative_log_path = "./my_custom_temp_logs/app_via_env.log"
    dot_env_path.write_text(f"LOGGING__LOG_FILE_PATH=\"{relative_log_path}\"\n")
    
    settings_with_temp_log = AppSettings(_env_file=dot_env_path)
    
    expected_log_file = (TEST_PROJECT_ROOT / Path(relative_log_path)).resolve()

    assert settings_with_temp_log.logging.LOG_FILE_PATH.resolve() == expected_log_file
    assert expected_log_file.parent.exists()

def test_db_path_creation_sqlite(tmp_path, monkeypatch):
    """Test that SQLite DB directory is handled correctly by AppSettings when path is from .env."""
    dot_env_path = tmp_path / ".env.dbtest"
    relative_db_path = "./my_test_data_dir_from_env/test_database.db"
    dot_env_path.write_text(f"DATABASE__DATABASE_URL=\"sqlite+aiosqlite:///{relative_db_path}\"\n")

    settings_with_relative_db = AppSettings(_env_file=dot_env_path)
    
    expected_db_file = (TEST_PROJECT_ROOT / Path(relative_db_path)).resolve()

    assert settings_with_relative_db.database.DATABASE_URL == f"sqlite+aiosqlite:///{expected_db_file}"
    assert expected_db_file.parent.exists()

if __name__ == "__main__":
    pytest.main([__file__])
