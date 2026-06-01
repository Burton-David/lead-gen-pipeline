"""Shared test fixtures.

Provides an isolated temp-file database and a deterministic fake LLM backend so the
chamber pipeline can be exercised end to end without the 4 GB Qwen2-7B model.
"""

import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio

from lead_gen_pipeline import database
from lead_gen_pipeline.config import settings


@pytest.fixture
def temp_db_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Point the database at an isolated temp file and reset cached engine state."""
    db_file = tmp_path / "test_leads.db"
    url = f"sqlite+aiosqlite:///{db_file}"
    monkeypatch.setattr(settings.database, "DATABASE_URL", url)
    database._reset_db_state_for_testing()
    yield url
    database._reset_db_state_for_testing()


@pytest_asyncio.fixture
async def initialized_db(temp_db_url: str) -> AsyncIterator[str]:
    """A temp database with tables created."""
    await database.init_db()
    yield temp_db_url


class FakeLLMBackend:
    """Deterministic :class:`~lead_gen_pipeline.llm_processor.LLMBackend` for tests.

    Returns ``listing_json`` for extraction prompts and ``nav_json`` for navigation
    prompts, so the full chamber flow can run without a real model. Records prompts.
    """

    def __init__(self, nav_json: str = "", listing_json: str = "") -> None:
        self.nav_json = nav_json or json.dumps(
            {"navigation_links": [], "confidence": 0}
        )
        self.listing_json = listing_json or json.dumps(
            {"business_listings": [], "pagination": {"next_page_url": None}}
        )
        self.prompts: list[str] = []
        self.ready_calls = 0

    def ensure_ready(self) -> bool:
        self.ready_calls += 1
        return True

    def generate(self, prompt: str, *, max_tokens: int, temperature: float) -> str:
        self.prompts.append(prompt)
        if "Extract business data" in prompt:
            return self.listing_json
        return self.nav_json


@pytest.fixture
def fake_backend() -> FakeLLMBackend:
    return FakeLLMBackend()


@pytest.fixture
def make_backend():
    """Factory for :class:`FakeLLMBackend` with custom canned JSON."""

    def _make(**kwargs: str) -> FakeLLMBackend:
        return FakeLLMBackend(**kwargs)

    return _make
