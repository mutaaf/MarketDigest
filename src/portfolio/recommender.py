"""'What should I buy next?' — ranked, explained recommendations.

Ranks candidates by fund/stock quality x how well they fill the portfolio's
gaps vs target allocation. Every recommendation carries plain-English reasons;
no manufactured confidence percentages. Each result set is snapshotted to
logs/compass_recs/ so the engine's track record can be graded later.
"""

import json
from datetime import datetime
from pathlib import Path

from src.utils.logging_config import get_logger

logger = get_logger("recommender")

PROJECT_ROOT = Path(__file__).parent.parent.parent
RECS_LOG_DIR = PROJECT_ROOT / "logs" / "compass_recs"

# Sensible long-term defaults until the user sets their own targets (Phase 2 UI)
DEFAULT_TARGETS = {"us_stock": 55.0, "intl_stock": 20.0, "bond": 15.0, "reit": 5.0, "cash": 5.0}

# Core low-cost candidates per asset class, in preference order
CORE_CANDIDATES = {
    "us_stock": ["VTI", "VOO", "SCHD", "VUG", "VTV"],
    "intl_stock": ["VXUS", "VEA", "VWO"],
    "bond": ["BND", "AGG", "BNDX"],
    "reit": ["VNQ", "SCHH"],
}


def recommend(portfolio: dict, valuation: dict, allocation: dict, limit: int = 5) -> dict:
    from config.settings import get_etf_universe
    from src.analysis.etf_scorer import score_etf
    from src.fetchers.etf_data import fetch_etf_profile

    targets = {**DEFAULT_TARGETS, **(portfolio.get("targets") or {})}
    actual = {c["key"]: c["weight"] for c in allocation.get("asset_classes", [])}
    total_value = valuation.get("total_value") or 0
    cash = valuation.get("cash") or 0

    if total_value <= 0:
        return {"recommendations": [], "gaps": [], "warnings": [],
                "note": "Add holdings or cash to get recommendations."}

    etf_config = {e["symbol"]: e for e in get_etf_universe()}
    held_weights = {h["symbol"]: h.get("weight", 0) for h in allocation.get("by_holding", [])}

    # Gaps: how far each asset class is below target, in points
    gaps = []
    for ac, target in targets.items():
        if ac == "cash":
            continue
        gap = target - actual.get(ac, 0)
        if gap > 2:
            gaps.append({"asset_class": ac, "target": target,
                         "actual": round(actual.get(ac, 0), 1), "gap": round(gap, 1)})
    gaps.sort(key=lambda g: -g["gap"])

    candidates, warnings = [], []
    classes_to_fill = [g["asset_class"] for g in gaps] or ["us_stock"]

    for ac in classes_to_fill:
        gap = next((g["gap"] for g in gaps if g["asset_class"] == ac), 0)
        for sym in CORE_CANDIDATES.get(ac, []):
            if held_weights.get(sym, 0) >= 8:
                continue  # already a meaningful position
            cfg = etf_config.get(sym)
            if cfg is None:
                continue
            profile = fetch_etf_profile(sym, cfg.get("yfinance", sym))
            if profile is None:
                warnings.append(f"Couldn't load data for {sym}; skipped it this time.")
                continue
            scored = score_etf(profile, cfg.get("category"))
            reasons = _etf_reasons(ac, gap, profile, scored, actual)
            rank = scored["overall"] * (1 + min(gap, 25) / 50)
            candidates.append({
                "symbol": sym,
                "name": profile.get("name") or cfg.get("name"),
                "type": "etf",
                "asset_class": ac,
                "grade": scored["grade"],
                "score": scored["overall"],
                "risk_level": scored["risk_level"],
                "expense_ratio": profile.get("expense_ratio"),
                "dividend_yield": profile.get("dividend_yield"),
                "return_5y": profile.get("return_5y"),
                "reasons": reasons,
                "_rank": rank,
            })

    candidates.extend(_stock_candidates(portfolio, allocation, held_weights, warnings))

    # One pick per asset class first, then best of the rest
    candidates.sort(key=lambda c: -c["_rank"])
    picked, seen_classes = [], set()
    for c in candidates:
        if c["asset_class"] not in seen_classes:
            picked.append(c)
            seen_classes.add(c["asset_class"])
    for c in candidates:
        if c not in picked:
            picked.append(c)
    picked = picked[:limit]
    for c in picked:
        c.pop("_rank", None)

    result = {
        "recommendations": picked,
        "gaps": gaps,
        "cash_available": cash,
        "warnings": warnings,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "targets_used": targets,
        "targets_are_default": not portfolio.get("targets"),
    }
    _snapshot(portfolio.get("name", "unknown"), result)
    return result


def _etf_reasons(ac: str, gap: float, profile: dict, scored: dict, actual: dict) -> list[str]:
    from src.portfolio.analyzer import ASSET_CLASS_LABELS
    reasons = []
    label = ASSET_CLASS_LABELS.get(ac, ac)
    if gap > 2:
        have = actual.get(ac, 0)
        if have < 1:
            reasons.append(f"You currently have no {label.lower()} exposure — this fills that gap.")
        else:
            reasons.append(f"You're underweight {label.lower()} ({have:.0f}% now, "
                           f"about {gap:.0f} points below target).")
    reasons.append(f"Overall grade {scored['grade']} ({scored['overall']:.0f}/100), "
                   f"{scored['risk_level'].lower()} risk.")
    er = profile.get("expense_ratio")
    if er is not None and er <= 0.15:
        reasons.append(f"Very cheap to own: {er:.2f}% a year — about ${er * 100:.0f} "
                       f"per $10,000 invested.")
    r5 = profile.get("return_5y")
    if r5 is not None:
        reasons.append(f"Returned {r5:.1f}% a year on average over the last five years.")
    dy = profile.get("dividend_yield")
    if dy is not None and dy >= 2.5:
        reasons.append(f"Pays {dy:.1f}% a year in dividends.")
    return reasons


def _stock_candidates(portfolio: dict, allocation: dict, held_weights: dict,
                      warnings: list) -> list[dict]:
    """Individual stock ideas — only offered if the user already holds single stocks,
    and only from cached fundamentals plus a small number of live fetches."""
    from config.settings import get_settings
    from src.analysis.daytrade_scorer import score_to_grade
    from src.analysis.fundamentals import fetch_fundamentals, score_fundamentals

    holds_stocks = any(h.get("instrument_type") == "stock"
                       for h in allocation.get("by_holding", []))
    if not holds_stocks:
        return []

    held_sectors = {s["key"] for s in allocation.get("sectors", [])[:3]}
    stocks = [s for s in get_settings().instruments.get("us_stocks", [])
              if s.get("enabled", True) and s["symbol"] not in held_weights]
    # Prefer sectors the portfolio is light in
    stocks.sort(key=lambda s: s.get("sector") in held_sectors)

    out, fetched = [], 0
    for s in stocks:
        if fetched >= 6:
            break
        fetched += 1
        fnd = fetch_fundamentals(s["symbol"], s.get("yfinance", s["symbol"]))
        if fnd is None:
            continue
        scores = score_fundamentals(fnd)
        composite = scores["composite"]
        if composite < 60:
            continue
        metrics = fnd.get("metrics", {})
        reasons = [f"Quality score {composite:.0f}/100 "
                   f"(grade {score_to_grade(composite)}) on valuation, profits, growth, and debt."]
        target, price = metrics.get("analyst_target"), metrics.get("current_price")
        if target and price and price > 0:
            upside = (target / price - 1) * 100
            if upside > 5:
                reasons.append(f"Analysts' average target is {upside:.0f}% above today's price.")
        if s.get("sector") and s["sector"] not in held_sectors:
            reasons.append(f"Adds {s['sector']} exposure your portfolio is light on.")
        out.append({
            "symbol": s["symbol"],
            "name": s.get("name", s["symbol"]),
            "type": "stock",
            "asset_class": "us_stock",
            "sector": s.get("sector"),
            "grade": score_to_grade(composite),
            "score": composite,
            "reasons": reasons,
            "_rank": composite * 0.9,  # ETFs get a slight edge for long-term default
        })
    return out


def _snapshot(portfolio_name: str, result: dict) -> None:
    try:
        RECS_LOG_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        path = RECS_LOG_DIR / f"{stamp}_{portfolio_name}.json"
        path.write_text(json.dumps(result, indent=2, default=str))
    except OSError as e:
        logger.warning(f"Could not snapshot recommendations: {e}")
