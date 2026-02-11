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


def save_snapshot(digest_data: dict, scoring_weights: dict, prompts_version: str,
                   digest_type: str = "daytrade") -> Path:
    """Save a digest snapshot for later review/grading.

    Args:
        digest_data: The accumulated digest data dict.
        scoring_weights: Scoring weights used (empty dict for non-daytrade).
        prompts_version: Version ID of prompts config.
        digest_type: Type of digest — "daytrade", "morning", "afternoon", "weekly".

    Returns the path to the saved snapshot file.
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    snapshot_id = f"{date_str}-{digest_type}"

    if digest_type == "daytrade":
        # Daytrade-specific: extract structured pick data
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
            "snapshot_id": snapshot_id,
            "digest_type": digest_type,
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
    else:
        # Non-daytrade: store the full digest data for retrace review
        snapshot = {
            "date": date_str,
            "snapshot_id": snapshot_id,
            "digest_type": digest_type,
            "timestamp": now.isoformat(),
            "scoring_weights": scoring_weights,
            "prompts_version": prompts_version,
            "data": _sanitize_value(digest_data),
            "grading": None,
        }

    RETRACE_DIR.mkdir(parents=True, exist_ok=True)
    path = RETRACE_DIR / f"{snapshot_id}.json"

    # Atomic write
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(snapshot, f, indent=2, default=str)
    tmp.rename(path)

    logger.info(f"Retrace snapshot saved: {path.name} ({digest_type})")
    return path


def load_snapshot(date_str: str) -> dict | None:
    """Load a snapshot by identifier.

    Accepts either a snapshot_id like '2026-02-11-daytrade' or a legacy
    date string like '2026-02-11'. Tries exact match first, then legacy.
    """
    # Try exact match (works for both new snapshot_id and legacy date-only names)
    path = RETRACE_DIR / f"{date_str}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    # Legacy fallback: if date_str looks like a plain date, it might be a legacy file
    # No additional fallback needed — the file either exists or doesn't
    return None


def save_snapshot_data(snapshot_id: str, data: dict) -> None:
    """Write snapshot data back to file (e.g. after grading).

    Args:
        snapshot_id: The snapshot identifier (file stem), e.g. '2026-02-11-daytrade'
                     or legacy '2026-02-11'.
    """
    path = RETRACE_DIR / f"{snapshot_id}.json"
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=str)
    tmp.rename(path)


def list_snapshots(limit: int = 30) -> list[dict]:
    """List snapshot metadata, newest first.

    The 'date' field is the unique snapshot identifier (file stem) used for
    load_snapshot() and grading. For new snapshots this is e.g. '2026-02-11-daytrade';
    for legacy snapshots it's just '2026-02-11'.
    """
    if not RETRACE_DIR.exists():
        return []

    files = sorted(RETRACE_DIR.glob("*.json"), reverse=True)
    results = []
    for f in files[:limit]:
        try:
            with open(f) as fp:
                data = json.load(fp)
            digest_type = data.get("digest_type", "daytrade")
            results.append({
                "date": data.get("snapshot_id", data.get("date", f.stem)),
                "timestamp": data.get("timestamp"),
                "pick_count": len(data.get("top_picks", [])),
                "has_grading": data.get("grading") is not None,
                "backfilled": data.get("backfilled", False),
                "scoring_weights": data.get("scoring_weights"),
                "prompts_version": data.get("prompts_version"),
                "digest_type": digest_type,
            })
        except Exception:
            continue
    return results
