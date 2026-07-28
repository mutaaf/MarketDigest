"""Regime tracker — tracks market regime shifts and adjusts strategy emphasis."""

import json
from datetime import datetime
from pathlib import Path
from collections import Counter

import yaml

from src.utils.logging_config import get_logger

logger = get_logger("innovation.regime")

SIGNALS_YAML = Path(__file__).parent.parent.parent / "config" / "signals.yaml"
STATE_PATH = Path(__file__).parent.parent.parent / "logs" / "innovation" / "regime_history.json"


def _load_history() -> list[dict]:
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_history(history: list[dict]):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Keep last 200 entries
    with open(STATE_PATH, "w") as f:
        json.dump(history[-200:], f, indent=2, default=str)


def track_regimes(signals: list[dict]):
    """Record current regime distribution from latest signal scan."""
    if not signals:
        return

    regimes = [s.get("regime", "unknown") for s in signals if s.get("regime")]
    if not regimes:
        return

    distribution = dict(Counter(regimes))
    total = len(regimes)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "distribution": distribution,
        "total_instruments": total,
        "dominant": max(distribution, key=distribution.get) if distribution else "unknown",
        "dominant_pct": round(max(distribution.values()) / total * 100, 0) if distribution else 0,
    }

    history = _load_history()
    history.append(entry)
    _save_history(history)


def detect_regime_shift() -> dict | None:
    """Detect if market regime has shifted significantly.

    Compares latest scan's distribution to the 5-scan rolling average.
    Returns shift info if > 20% change, else None.
    """
    history = _load_history()
    if len(history) < 3:
        return None

    current = history[-1]["distribution"]
    current_total = history[-1]["total_instruments"]

    # 5-scan rolling average
    recent = history[-6:-1] if len(history) >= 6 else history[:-1]
    avg_dist = Counter()
    for h in recent:
        for regime, count in h["distribution"].items():
            avg_dist[regime] += count
    total_avg = sum(avg_dist.values()) or 1

    # Compare
    shifts = {}
    all_regimes = set(list(current.keys()) + list(avg_dist.keys()))
    for regime in all_regimes:
        curr_pct = current.get(regime, 0) / current_total * 100 if current_total > 0 else 0
        avg_pct = avg_dist.get(regime, 0) / total_avg * 100
        diff = curr_pct - avg_pct
        if abs(diff) > 15:
            shifts[regime] = {"current_pct": round(curr_pct), "avg_pct": round(avg_pct), "shift": round(diff)}

    if not shifts:
        return None

    return {
        "timestamp": datetime.now().isoformat(),
        "shifts": shifts,
        "current": current,
        "message": _format_shift(shifts),
    }


def _format_shift(shifts: dict) -> str:
    parts = []
    for regime, data in shifts.items():
        direction = "up" if data["shift"] > 0 else "down"
        parts.append(f"{regime} {direction} ({data['avg_pct']}% → {data['current_pct']}%)")
    return "Regime shift: " + ", ".join(parts)


def compute_regime_overrides() -> dict:
    """Compute strategy boost/suppress overrides based on current regime.

    Returns dict to write to signals.yaml regime_overrides section.
    """
    history = _load_history()
    if not history:
        return {}

    current = history[-1]
    dominant = current.get("dominant", "ranging")
    dominant_pct = current.get("dominant_pct", 0)

    overrides = {}

    if dominant_pct < 40:
        # No clear dominant regime — don't override
        return {}

    if dominant in ("trending_up", "trending_down"):
        overrides = {
            "boost": ["ema_trend_follow", "rsi_momentum"],
            "suppress": ["bollinger_mean_reversion"],
            "note": f"Market is {dominant_pct}% {dominant} — favoring trend strategies",
        }
    elif dominant == "ranging":
        overrides = {
            "boost": ["bollinger_mean_reversion", "pivot_bounce"],
            "suppress": ["donchian_breakout"],
            "note": f"Market is {dominant_pct}% ranging — favoring mean reversion",
        }
    elif dominant == "volatile":
        overrides = {
            "boost": ["donchian_breakout", "swing_reversal"],
            "suppress": ["bollinger_mean_reversion"],
            "note": f"Market is {dominant_pct}% volatile — favoring breakouts",
        }
    elif dominant == "low_vol":
        overrides = {
            "boost": ["volatility_squeeze", "donchian_breakout"],
            "suppress": [],
            "note": f"Market is {dominant_pct}% low vol — squeeze breakout setup",
        }

    return overrides


def get_regime_summary() -> dict:
    """Get regime summary for dashboard/reports."""
    history = _load_history()
    if not history:
        return {"current": {}, "history_length": 0}

    current = history[-1]
    shift = detect_regime_shift()

    return {
        "current": current,
        "shift": shift,
        "history_length": len(history),
        "overrides": compute_regime_overrides(),
    }
