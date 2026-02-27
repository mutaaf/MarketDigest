"""Shared test fixtures — ensures no real API keys leak into tests."""

import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def clear_api_keys(monkeypatch):
    """Remove all API keys from environment during tests."""
    keys_to_clear = [
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
        "TWELVEDATA_API_KEY", "FINNHUB_API_KEY",
        "FRED_API_KEY", "NEWSAPI_KEY",
        "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
    ]
    for key in keys_to_clear:
        monkeypatch.delenv(key, raising=False)
