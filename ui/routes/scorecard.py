"""Score Card endpoints — instrument scoring and grading."""

import time

from fastapi import APIRouter, HTTPException, Query

import yfinance as yf

from config.settings import get_all_yfinance_tickers
from src.analysis.technicals import full_analysis
from src.analysis.daytrade_scorer import score_instrument, score_to_grade
from src.retrace.scoring_config import load_scoring_weights
from src.retrace.snapshot import list_snapshots, load_snapshot

router = APIRouter(prefix="/api/scorecard", tags=["scorecard"])

# ── Cache (4-hour TTL) ────────────────────────────────────────

_CACHE_TTL = 4 * 60 * 60  # 4 hours in seconds

_all_cards_cache: dict = {"data": None, "ts": 0.0}
_detail_cache: dict[str, dict] = {}  # symbol -> {"data": ..., "ts": float}


# ── Grade helpers ─────────────────────────────────────────────

_score_to_grade = score_to_grade


def _build_verdict(score: float, trend: str | None, signals: list[str]) -> str:
    top_signal = signals[0] if signals else "no clear catalyst"
    trend_label = (trend or "neutral").replace("_", " ")

    if score >= 80:
        return f"Strong setup \u2014 {trend_label} trend, {top_signal}"
    if score >= 65:
        return f"Solid momentum \u2014 {top_signal}"
    if score >= 50:
        return "Neutral \u2014 waiting for clearer signals"
    if score >= 40:
        return "Weak \u2014 limited opportunity"
    return "Avoid \u2014 limited opportunity"


def _build_history(symbol: str) -> dict:
    """Scan graded snapshots for a symbol's pick history."""
    metas = list_snapshots(limit=200)
    appearances = 0
    wins = 0
    losses = 0
    scratches = 0
    r_multiples: list[float] = []
    recent: list[dict] = []

    for meta in metas:
        if not meta.get("has_grading"):
            continue
        snap = load_snapshot(meta["date"])
        if not snap or not snap.get("grading"):
            continue

        grading = snap["grading"]
        picks = grading.get("picks", [])
        for pick in picks:
            if pick.get("symbol") != symbol:
                continue
            appearances += 1
            outcome = pick.get("outcome", "pending")
            if outcome == "win":
                wins += 1
            elif outcome == "loss":
                losses += 1
            elif outcome == "scratch":
                scratches += 1

            r = pick.get("r_multiple")
            if r is not None:
                r_multiples.append(r)

            recent.append({
                "date": meta["date"],
                "outcome": outcome,
                "entry": pick.get("entry"),
                "r_multiple": r,
                "actual_return_pct": pick.get("actual_return_pct"),
            })

    recent = recent[:5]  # last 5
    total_decided = wins + losses
    win_rate = round(wins / total_decided * 100, 1) if total_decided > 0 else None
    avg_r = round(sum(r_multiples) / len(r_multiples), 2) if r_multiples else None

    return {
        "appearances": appearances,
        "wins": wins,
        "losses": losses,
        "scratches": scratches,
        "win_rate": win_rate,
        "avg_r": avg_r,
        "recent": recent,
    }


def _run_analysis(sym: str, weights: dict) -> dict | None:
    """Fetch data and run TA + scoring for a single symbol."""
    try:
        ticker = yf.Ticker(sym)
        df = ticker.history(period="6mo")
        if df is None or df.empty or len(df) < 14:
            return None

        ta = full_analysis(df, ticker=sym)
        if ta.get("error"):
            return None

        # Try to get a friendly name from yfinance info
        name = sym
        try:
            name = ticker.info.get("shortName") or ticker.info.get("longName") or sym
        except Exception:
            pass

        price = float(df["Close"].iloc[-1])
        price_data = {"price": price, "ticker": sym, "name": name}

        scored = score_instrument(ta, price_data, weights=weights)
        if not scored:
            return None

        return {"ta": ta, "scored": scored}
    except Exception:
        return None


# ── Endpoints ─────────────────────────────────────────────────

@router.get("/all")
def get_all_scorecards(refresh: bool = Query(False)):
    """Compact score card data for all enabled instruments.

    Results are cached for 4 hours. Pass ?refresh=true to force a fresh fetch.
    """
    now = time.time()
    if not refresh and _all_cards_cache["data"] is not None and (now - _all_cards_cache["ts"]) < _CACHE_TTL:
        return _all_cards_cache["data"]

    tickers = get_all_yfinance_tickers()
    weights = load_scoring_weights()
    cards = []

    for t in tickers:
        sym = t.get("yfinance") or t.get("symbol", "")
        if not sym:
            continue

        result = _run_analysis(sym, weights)
        if not result:
            continue

        scored = result["scored"]
        grade = _score_to_grade(scored["score"])

        cards.append({
            "symbol": scored["symbol"],
            "name": t.get("name", scored["name"]),
            "grade": grade,
            "score": scored["score"],
            "trend": scored.get("trend"),
            "trend_emoji": scored.get("trend_emoji", ""),
            "rsi": scored.get("rsi"),
            "signals": scored.get("signals", []),
        })

    # Sort by score descending
    cards.sort(key=lambda c: c["score"], reverse=True)

    _all_cards_cache["data"] = cards
    _all_cards_cache["ts"] = now

    return cards


@router.get("/{symbol}")
def get_scorecard_detail(symbol: str, refresh: bool = Query(False)):
    """Full score card detail for a single instrument.

    Results are cached for 4 hours. Pass ?refresh=true to force a fresh fetch.
    """
    sym_upper = symbol.upper()
    now = time.time()
    cached = _detail_cache.get(sym_upper)
    if not refresh and cached and (now - cached["ts"]) < _CACHE_TTL:
        return cached["data"]

    weights = load_scoring_weights()
    result = _run_analysis(sym_upper, weights)

    if not result:
        raise HTTPException(404, f"No data available for {symbol}")

    ta = result["ta"]
    scored = result["scored"]
    grade = _score_to_grade(scored["score"])
    verdict = _build_verdict(scored["score"], scored.get("trend"), scored.get("signals", []))
    history = _build_history(scored["symbol"])

    technicals = {
        "rsi": ta.get("rsi"),
        "rsi_label": ta.get("rsi_label"),
        "sma_20": ta.get("sma_20"),
        "sma_50": ta.get("sma_50"),
        "ema_12": ta.get("ema_12"),
        "ema_26": ta.get("ema_26"),
        "atr": ta.get("atr"),
        "pivots": ta.get("pivots", {}),
        "support_resistance": ta.get("support_resistance", {}),
        "volume_ratio": ta.get("volume_ratio"),
        "gap_pct": ta.get("gap_pct"),
    }

    setup = {
        "entry": scored["entry"],
        "target": scored["target"],
        "stop": scored["stop"],
        "risk_reward": scored["risk_reward"],
        "signals": scored.get("signals", []),
    }

    response = {
        "symbol": scored["symbol"],
        "name": scored.get("name", symbol),
        "grade": grade,
        "score": scored["score"],
        "trend": scored.get("trend"),
        "trend_emoji": scored.get("trend_emoji", ""),
        "rsi": scored.get("rsi"),
        "signals": scored.get("signals", []),
        "verdict": verdict,
        "setup": setup,
        "technicals": technicals,
        "history": history,
    }

    _detail_cache[sym_upper] = {"data": response, "ts": now}

    return response
