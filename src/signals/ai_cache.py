"""AI insight cache — persist AI explanations with TTL and staleness tracking."""

import json
from datetime import datetime
from pathlib import Path

from src.utils.logging_config import get_logger

logger = get_logger("ai_cache")

CACHE_PATH = Path(__file__).parent.parent.parent / "logs" / "ai_insights.json"

# TTL settings
FRESH_TTL_MINUTES = 30       # "Fresh" for 30 min
STALE_TTL_MINUTES = 120      # "Stale" after 2 hours — still shown but flagged
EXPIRED_TTL_MINUTES = 480    # "Expired" after 8 hours — auto-refresh on next view


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(cache: dict):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if len(cache) > 500:
        sorted_keys = sorted(cache.keys(), key=lambda k: cache[k].get("timestamp", ""), reverse=True)
        cache = {k: cache[k] for k in sorted_keys[:500]}
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2, default=str)


def _get_age_info(timestamp_str: str) -> dict:
    """Compute age and freshness status from a timestamp string."""
    try:
        ts = datetime.fromisoformat(timestamp_str)
    except (ValueError, TypeError):
        return {"age_minutes": 9999, "age_label": "unknown", "freshness": "expired"}

    age = datetime.now() - ts
    age_minutes = age.total_seconds() / 60

    if age_minutes < 1:
        age_label = "just now"
    elif age_minutes < 60:
        age_label = f"{int(age_minutes)}m ago"
    elif age_minutes < 1440:
        age_label = f"{int(age_minutes / 60)}h ago"
    else:
        age_label = f"{int(age_minutes / 1440)}d ago"

    if age_minutes <= FRESH_TTL_MINUTES:
        freshness = "fresh"
    elif age_minutes <= STALE_TTL_MINUTES:
        freshness = "stale"
    else:
        freshness = "expired"

    return {
        "age_minutes": round(age_minutes, 1),
        "age_label": age_label,
        "freshness": freshness,
    }


def get_cached_insight(signal_id: str) -> dict | None:
    """Get a cached AI insight with age info.

    Returns dict with: explanation, timestamp, age_label, freshness
    Or None if not cached.
    """
    cache = _load_cache()
    entry = cache.get(signal_id)
    if not entry:
        return None

    age_info = _get_age_info(entry.get("timestamp", ""))
    return {
        "explanation": entry.get("explanation", ""),
        "timestamp": entry.get("timestamp", ""),
        "symbol": entry.get("symbol", ""),
        "strategy": entry.get("strategy", ""),
        **age_info,
    }


def get_cached_explanation(signal_id: str) -> str | None:
    """Get just the explanation text (backward compat)."""
    info = get_cached_insight(signal_id)
    return info["explanation"] if info else None


def is_fresh(signal_id: str) -> bool:
    """Check if cached insight is still fresh (within TTL)."""
    info = get_cached_insight(signal_id)
    return info is not None and info["freshness"] == "fresh"


def is_expired(signal_id: str) -> bool:
    """Check if cached insight has fully expired."""
    info = get_cached_insight(signal_id)
    if info is None:
        return True
    return info["freshness"] == "expired"


def cache_insight(signal_id: str, explanation: str, symbol: str = "", strategy: str = ""):
    """Cache an AI insight for a signal."""
    cache = _load_cache()
    cache[signal_id] = {
        "explanation": explanation,
        "symbol": symbol,
        "strategy": strategy,
        "timestamp": datetime.now().isoformat(),
    }
    _save_cache(cache)


def invalidate(signal_id: str):
    """Remove a cached insight (forces regeneration)."""
    cache = _load_cache()
    if signal_id in cache:
        del cache[signal_id]
        _save_cache(cache)


def get_all_cached() -> dict:
    """Get entire cache with age info."""
    cache = _load_cache()
    result = {}
    for sig_id, entry in cache.items():
        age_info = _get_age_info(entry.get("timestamp", ""))
        result[sig_id] = {**entry, **age_info}
    return result


def generate_and_cache_insight(signal_dict: dict, market_context: dict | None = None,
                               force: bool = False) -> str:
    """Generate an AI insight and cache it.

    Args:
        signal_dict: Signal data dict
        market_context: Optional news/sentiment/events context
        force: If True, regenerate even if cached and fresh

    Returns:
        The AI explanation string
    """
    signal_id = signal_dict.get("id", "")

    # Check cache (skip if force=True)
    if not force and signal_id:
        info = get_cached_insight(signal_id)
        if info and info["freshness"] in ("fresh", "stale"):
            return info["explanation"]

    # Generate new insight
    try:
        from src.analysis.llm_analyzer import MarketAnalyzer

        enriched = {**signal_dict}
        if market_context:
            enriched["market_context"] = market_context

        analyzer = MarketAnalyzer()
        explanation = analyzer.analyze_section("signal_explanation", enriched)

        if explanation and signal_id:
            cache_insight(signal_id, explanation,
                          signal_dict.get("symbol", ""),
                          signal_dict.get("strategy_name", ""))
            logger.info(f"AI insight cached for {signal_dict.get('symbol', '?')} ({signal_id})")
            return explanation

    except Exception as e:
        logger.warning(f"AI insight generation failed for {signal_id}: {e}")

    # Fall back to stale cache if generation failed
    if signal_id:
        info = get_cached_insight(signal_id)
        if info:
            return info["explanation"]

    return ""


def enrich_signals_with_insights(signals: list[dict]) -> list[dict]:
    """Add cached AI explanations + freshness info to signal dicts."""
    cache = _load_cache()
    for sig in signals:
        sig_id = sig.get("id", "")
        if sig_id and sig_id in cache:
            entry = cache[sig_id]
            age_info = _get_age_info(entry.get("timestamp", ""))
            sig["ai_explanation"] = entry.get("explanation", "")
            sig["ai_timestamp"] = entry.get("timestamp", "")
            sig["ai_age_label"] = age_info["age_label"]
            sig["ai_freshness"] = age_info["freshness"]
        else:
            sig["ai_explanation"] = sig.get("ai_explanation", "")
            sig["ai_timestamp"] = ""
            sig["ai_age_label"] = ""
            sig["ai_freshness"] = ""
    return signals
