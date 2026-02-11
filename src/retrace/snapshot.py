"""Retrace snapshot — save/load full daytrade digest snapshots for grading."""

import json
import math
from datetime import datetime
from pathlib import Path

from config.settings import PROJECT_ROOT
from src.utils.logging_config import get_logger

logger = get_logger("retrace.snapshot")

RETRACE_DIR = PROJECT_ROOT / "logs" / "retrace"


def _sanitize_value(v):
    """Make a value JSON-safe (handle NaN, Inf, etc.)."""
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    if isinstance(v, dict):
        return {k: _sanitize_value(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [_sanitize_value(item) for item in v]
    return v


def save_snapshot(digest_data: dict, scoring_weights: dict, prompts_version: str) -> Path:
    """Save a full daytrade digest snapshot for later grading.

    Returns the path to the saved snapshot file.
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    # Extract relevant price data (just what we need, not the full objects)
    prices = {}
    raw_prices = digest_data.get("prices", {})
    for sym, pd_dict in raw_prices.items():
        if isinstance(pd_dict, dict):
            prices[sym] = {
                "price": pd_dict.get("price"),
                "open": pd_dict.get("open"),
                "high": pd_dict.get("high"),
                "low": pd_dict.get("low"),
                "volume": pd_dict.get("volume"),
                "change_pct": pd_dict.get("change_pct"),
            }

    snapshot = {
        "date": date_str,
        "timestamp": now.isoformat(),
        "scoring_weights": scoring_weights,
        "prompts_version": prompts_version,
        "top_picks": _sanitize_value(digest_data.get("top_picks", [])),
        "honorable_mentions": _sanitize_value(digest_data.get("honorable_mentions", [])),
        "avoid_list": _sanitize_value(digest_data.get("avoid_list", [])),
        "prices": _sanitize_value(prices),
        "sentiment": _sanitize_value(digest_data.get("sentiment")),
        "grading": None,
    }

    RETRACE_DIR.mkdir(parents=True, exist_ok=True)
    path = RETRACE_DIR / f"{date_str}.json"

    # Atomic write
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(snapshot, f, indent=2, default=str)
    tmp.rename(path)

    logger.info(f"Retrace snapshot saved: {path.name} ({len(snapshot['top_picks'])} picks)")
    return path


def load_snapshot(date_str: str) -> dict | None:
    """Load a snapshot by date string (YYYY-MM-DD)."""
    path = RETRACE_DIR / f"{date_str}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def save_snapshot_data(date_str: str, data: dict) -> None:
    """Write snapshot data back to file (e.g. after grading)."""
    path = RETRACE_DIR / f"{date_str}.json"
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=str)
    tmp.rename(path)


def list_snapshots(limit: int = 30) -> list[dict]:
    """List snapshot metadata, newest first."""
    if not RETRACE_DIR.exists():
        return []

    files = sorted(RETRACE_DIR.glob("*.json"), reverse=True)
    results = []
    for f in files[:limit]:
        try:
            with open(f) as fp:
                data = json.load(fp)
            results.append({
                "date": data.get("date", f.stem),
                "timestamp": data.get("timestamp"),
                "pick_count": len(data.get("top_picks", [])),
                "has_grading": data.get("grading") is not None,
                "scoring_weights": data.get("scoring_weights"),
                "prompts_version": data.get("prompts_version"),
            })
        except Exception:
            continue
    return results
