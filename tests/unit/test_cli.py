"""Tests for the Typer CLI.

The original CLI died at import; these confirm every command is wired and runnable.
Network and the scraper are mocked, so no live requests are made.
"""

import asyncio
import csv
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from lead_gen_pipeline.cli import app
from lead_gen_pipeline.database import save_lead

runner = CliRunner()


def test_config_command_runs():
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0


def test_init_command_creates_db(temp_db_url):
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "initialized" in result.stdout.lower()


def test_stats_empty_database(initialized_db):
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "No data" in result.stdout


def test_export_empty_database(initialized_db, tmp_path):
    out = tmp_path / "out.csv"
    result = runner.invoke(app, ["export", "-o", str(out)])
    assert result.exit_code == 0
    assert "No data" in result.stdout
    assert not out.exists()


def test_export_writes_rows(initialized_db, tmp_path):
    asyncio.run(
        save_lead(
            {
                "company_name": "Acme Co",
                "website": "https://acme.com",
                "scraped_from_url": "https://acme.com",
                "emails": ["info@acme.com"],
            }
        )
    )
    out = tmp_path / "leads.csv"
    result = runner.invoke(app, ["export", "-o", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    rows = list(csv.DictReader(out.open()))
    assert rows[0]["company_name"] == "Acme Co"
    assert "info@acme.com" in rows[0]["emails"]


def test_test_command_extracts_without_network(monkeypatch):
    from lead_gen_pipeline import crawler as crawler_module

    html = "<html><head><title>Acme Solutions</title></head><body></body></html>"
    monkeypatch.setattr(
        crawler_module.AsyncWebCrawler,
        "fetch_page",
        AsyncMock(return_value=(html, 200, "http://acme.test")),
    )
    monkeypatch.setattr(crawler_module.AsyncWebCrawler, "close", AsyncMock())

    result = runner.invoke(app, ["test", "http://acme.test"])
    assert result.exit_code == 0


def test_test_command_reports_fetch_failure(monkeypatch):
    from lead_gen_pipeline import crawler as crawler_module

    monkeypatch.setattr(
        crawler_module.AsyncWebCrawler,
        "fetch_page",
        AsyncMock(return_value=(None, 404, "http://missing.test")),
    )
    monkeypatch.setattr(crawler_module.AsyncWebCrawler, "close", AsyncMock())

    result = runner.invoke(app, ["test", "http://missing.test"])
    assert result.exit_code == 0
    assert "Failed to fetch" in result.stdout
