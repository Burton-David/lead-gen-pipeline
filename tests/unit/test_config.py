"""Tests for layered application configuration."""

from pathlib import Path

import pytest

from lead_gen_pipeline.config import (
    AppSettings,
    CrawlerSettings,
    LLMSettings,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_default_settings_load_correctly():
    settings = AppSettings(_env_file=None)

    assert settings.PROJECT_NAME == "Lead Generation Pipeline"
    assert settings.BASE_DIR == PROJECT_ROOT
    assert settings.MAX_PIPELINE_CONCURRENCY == 5

    assert settings.crawler.DEFAULT_TIMEOUT_SECONDS == 30
    assert settings.crawler.RESPECT_ROBOTS_TXT is True
    assert settings.crawler.ROBOTS_TXT_USER_AGENT == "*"

    assert settings.database.DATABASE_URL.startswith("sqlite+aiosqlite:///")
    assert settings.database.ECHO_SQL is False

    assert settings.llm.CONTEXT_SIZE == 32768
    assert settings.llm.MAX_TOKENS == 4096
    assert settings.llm.TEMPERATURE == 0.0
    assert settings.llm.MODEL_PATH.name == "qwen2-7b-instruct-q4_k_m.gguf"


def test_env_var_overrides(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", "Overridden")
    monkeypatch.setenv("LOGGING__LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("CRAWLER__DEFAULT_TIMEOUT_SECONDS", "50")
    monkeypatch.setenv("CRAWLER__RESPECT_ROBOTS_TXT", "false")
    monkeypatch.setenv("LLM__CONTEXT_SIZE", "8192")
    monkeypatch.setenv("MAX_PIPELINE_CONCURRENCY", "12")

    settings = AppSettings(_env_file=None)

    assert settings.PROJECT_NAME == "Overridden"
    assert settings.logging.LOG_LEVEL == "DEBUG"
    assert settings.crawler.DEFAULT_TIMEOUT_SECONDS == 50
    assert settings.crawler.RESPECT_ROBOTS_TXT is False
    assert settings.llm.CONTEXT_SIZE == 8192
    assert settings.MAX_PIPELINE_CONCURRENCY == 12


def test_dotenv_file_override(tmp_path):
    env_file = tmp_path / ".env.test"
    csv_file = tmp_path / "seed.csv"
    csv_file.touch()
    env_file.write_text(
        'PROJECT_NAME="From DotEnv"\n'
        "CRAWLER__MAX_RETRIES=7\n"
        f'INPUT_URLS_CSV="{csv_file}"\n'
    )
    settings = AppSettings(_env_file=env_file)
    assert settings.PROJECT_NAME == "From DotEnv"
    assert settings.crawler.MAX_RETRIES == 7
    assert settings.INPUT_URLS_CSV.resolve() == csv_file.resolve()


def test_crawler_delay_validation():
    with pytest.raises(ValueError, match="MAX_DELAY_PER_DOMAIN_SECONDS must be >="):
        CrawlerSettings(
            MIN_DELAY_PER_DOMAIN_SECONDS=5.0, MAX_DELAY_PER_DOMAIN_SECONDS=2.0
        )
    # Valid ordering should not raise.
    CrawlerSettings(MIN_DELAY_PER_DOMAIN_SECONDS=2.0, MAX_DELAY_PER_DOMAIN_SECONDS=5.0)


def test_llm_settings_bounds():
    with pytest.raises(ValueError):
        LLMSettings(CONTEXT_SIZE=10)  # below the minimum of 512
    with pytest.raises(ValueError):
        LLMSettings(TEMPERATURE=5.0)  # above the maximum of 2.0


def test_log_dir_created(tmp_path):
    env_file = tmp_path / ".env.log"
    env_file.write_text('LOGGING__LOG_FILE_PATH="./logs_under_test/app.log"\n')
    settings = AppSettings(_env_file=env_file)
    assert settings.logging.LOG_FILE_PATH.parent.exists()
