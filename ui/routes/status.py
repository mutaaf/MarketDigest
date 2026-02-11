"""Dashboard status endpoint."""

import json
from pathlib import Path

from fastapi import APIRouter

from config.settings import get_settings, PROJECT_ROOT

router = APIRouter(prefix="/api", tags=["status"])

HISTORY_FILE = PROJECT_ROOT / "logs" / "digest_history.json"


@router.get("/status")
def get_status():
    """Dashboard health: API configs, cache stats, onboarding status."""
    settings = get_settings()

    apis = {
        "telegram": {
            "configured": bool(settings.telegram.bot_token and settings.telegram.chat_id),
            "name": "Telegram",
        },
        "yfinance": {
            "configured": True,
            "name": "yFinance (no key needed)",
        },
        "twelvedata": {
            "configured": bool(settings.api_keys.twelvedata),
            "name": "Twelve Data",
        },
        "finnhub": {
            "configured": bool(settings.api_keys.finnhub),
            "name": "Finnhub",
        },
        "fred": {
            "configured": bool(settings.api_keys.fred),
            "name": "FRED",
        },
        "newsapi": {
            "configured": bool(settings.api_keys.newsapi),
            "name": "NewsAPI",
        },
        "feargreed": {
            "configured": True,
            "name": "Fear & Greed (no key needed)",
        },
        "anthropic": {
            "configured": bool(settings.llm_keys.anthropic),
            "name": "Anthropic (Claude)",
        },
        "openai": {
            "configured": bool(settings.llm_keys.openai),
            "name": "OpenAI",
        },
        "gemini": {
            "configured": bool(settings.llm_keys.gemini),
            "name": "Google Gemini",
        },
    }

    # Cache stats
    cache_dir = settings.cache_dir
    cache_files = list(cache_dir.glob("*.json")) if cache_dir.exists() else []
    cache_size = sum(f.stat().st_size for f in cache_files)

    # Recent history
    recent_history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text())
            recent_history = history[-10:]
        except (json.JSONDecodeError, OSError):
            pass

    # Onboarding: check minimum config
    required_configured = bool(
        settings.telegram.bot_token
        and settings.telegram.chat_id
    )

    return {
        "apis": apis,
        "cache": {
            "file_count": len(cache_files),
            "total_size_bytes": cache_size,
        },
        "recent_history": recent_history,
        "onboarding_complete": required_configured,
        "timezone": settings.timezone,
        "log_level": settings.log_level,
        "has_llm_key": settings.has_llm_key(),
    }
