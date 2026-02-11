"""Retrace backfill — retroactively generate snapshots for past dates."""

import json
import math
from datetime import datetime
from pathlib import Path

import yfinance as yf

from config.settings import get_all_yfinance_tickers
from src.analysis.technicals import full_analysis
from src.analysis.daytrade_scorer import score_instrument
from src.retrace.scoring_config import load_scoring_weights
from src.retrace.snapshot import RETRACE_DIR, _sanitize_value
from src.utils.logging_config import get_logger

logger = get_logger("retrace.backfill")


def backfill_snapshot(
    target_date: str,
    scoring_weights: dict | None = None,
    overwrite: bool = False,
) -> dict:
    """Generate a retroactive snapshot for a past date.

    Fetches historical data, truncates to target_date, runs the same
    scoring pipeline used in live digests, and saves the snapshot.

    Args:
        target_date: YYYY-MM-DD string for the date to backfill.
        scoring_weights: Optional explicit weights. Loads from config if None.
        overwrite: If True, overwrite an existing snapshot for this date.

    Returns:
        The saved snapshot dict.

    Raises:
        ValueError: If the date is invalid, a weekend, today/future, or
                     a snapshot already exists (and overwrite=False).
    """
    # ── Validate date ────────────────────────────────────────────
    try:
        dt = datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {target_date}. Use YYYY-MM-DD.")

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if dt >= today:
        raise ValueError("Cannot backfill today or future dates.")

    if dt.weekday() >= 5:  # Saturday=5, Sunday=6
        raise ValueError(f"{target_date} is a weekend — no trading day.")

    # ── Check for existing snapshot ──────────────────────────────
    RETRACE_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_id = f"{target_date}-daytrade"
    path = RETRACE_DIR / f"{snapshot_id}.json"
    # Also check legacy filename
    legacy_path = RETRACE_DIR / f"{target_date}.json"
    if (path.exists() or legacy_path.exists()) and not overwrite:
        raise ValueError(f"Snapshot for {target_date} already exists. Use overwrite=True to replace.")

    # ── Load scoring weights ─────────────────────────────────────
    weights = scoring_weights or load_scoring_weights()

    # ── Score each instrument ────────────────────────────────────
    tickers = get_all_yfinance_tickers()
    scored = []
    prices = {}

    for inst in tickers:
        sym = inst.get("yfinance") or inst.get("symbol")
        if not sym:
            continue

        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="6mo")
            if hist.empty:
                continue

            # Truncate to rows on or before target_date
            hist = hist[hist.index.normalize() <= dt]
            if hist.empty or len(hist) < 14:
                continue

            # Run technical analysis on truncated history
            ta = full_analysis(hist, ticker=sym)
            if ta.get("error"):
                continue

            # Extract last-row price data
            last = hist.iloc[-1]
            prev_close = float(hist.iloc[-2]["Close"]) if len(hist) >= 2 else None
            price = float(last["Close"])
            change_pct = round(((price - prev_close) / prev_close) * 100, 2) if prev_close else None

            price_data = {
                "ticker": sym,
                "name": inst.get("name", sym),
                "price": price,
                "open": float(last["Open"]),
                "high": float(last["High"]),
                "low": float(last["Low"]),
                "volume": int(last["Volume"]) if last["Volume"] else 0,
                "change_pct": change_pct,
            }

            result = score_instrument(ta, price_data, weights)
            if result:
                scored.append(result)
                prices[sym] = {
                    "price": price_data["price"],
                    "open": price_data["open"],
                    "high": price_data["high"],
                    "low": price_data["low"],
                    "volume": price_data["volume"],
                    "change_pct": price_data["change_pct"],
                }
        except Exception as e:
            logger.debug(f"Backfill skip {sym}: {e}")
            continue

    if not scored:
        raise ValueError(f"No instruments could be scored for {target_date}.")

    # ── Sort and rank ────────────────────────────────────────────
    scored.sort(key=lambda x: x["score"], reverse=True)
    top_picks = scored[:10]
    honorable_mentions = scored[10:15]
    avoid_list = scored[-5:][::-1] if len(scored) >= 15 else []

    # ── Build & save snapshot ────────────────────────────────────
    snapshot = {
        "date": target_date,
        "snapshot_id": snapshot_id,
        "digest_type": "daytrade",
        "timestamp": datetime.now().isoformat(),
        "scoring_weights": weights,
        "prompts_version": "backfill",
        "top_picks": _sanitize_value(top_picks),
        "honorable_mentions": _sanitize_value(honorable_mentions),
        "avoid_list": _sanitize_value(avoid_list),
        "prices": _sanitize_value(prices),
        "sentiment": None,
        "backfilled": True,
        "grading": None,
    }

    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(snapshot, f, indent=2, default=str)
    tmp.rename(path)

    logger.info(f"Backfill snapshot saved: {snapshot_id} ({len(top_picks)} picks)")
    return snapshot
