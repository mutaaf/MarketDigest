"""ETF scoring — safety, growth, income, diversification, cost → overall grade.

All sub-scores are 0-100 where higher is better. risk_level is a plain-English
label derived from volatility, not a score, so it can't be misread.
"""

from pathlib import Path

import yaml

from src.analysis.daytrade_scorer import score_to_grade

PROJECT_ROOT = Path(__file__).parent.parent.parent
SCORING_YAML = PROJECT_ROOT / "config" / "scoring.yaml"

DEFAULT_ETF_WEIGHTS = {
    "safety": 0.25,
    "growth": 0.30,
    "income": 0.10,
    "diversification": 0.20,
    "cost": 0.15,
}

# Categories that are inherently broad (whole-market exposure in one fund)
_BROAD_CATEGORIES = {
    "us_broad", "intl_broad", "intl_developed", "intl_emerging",
    "bond_total", "us_large_growth", "us_large_value", "dividend", "factor",
}
_NARROW_CATEGORIES = {"thematic", "gold", "commodity", "covered_call"}


def load_etf_weights() -> dict[str, float]:
    try:
        with open(SCORING_YAML) as f:
            data = yaml.safe_load(f) or {}
        weights = data.get("etf_weights")
        if weights and abs(sum(weights.values()) - 1.0) < 0.01:
            return weights
    except Exception:
        pass
    return dict(DEFAULT_ETF_WEIGHTS)


def _score_safety(profile: dict) -> float:
    vol = profile.get("volatility_1y")
    aum = profile.get("aum")
    score = 50.0
    if vol is not None:
        if vol < 8:
            score = 95
        elif vol < 13:
            score = 85
        elif vol < 18:
            score = 70
        elif vol < 25:
            score = 50
        elif vol < 35:
            score = 30
        else:
            score = 15
    if aum is not None and aum < 1e9:
        score -= 10  # small funds carry closure/liquidity risk
    return max(0, min(100, score))


def _score_growth(profile: dict) -> float:
    scores = []
    for key, weight in [("return_3y", 0.4), ("return_5y", 0.4), ("return_1y", 0.2)]:
        r = profile.get(key)
        if r is None:
            continue
        if r > 15:
            s = 95
        elif r > 10:
            s = 80
        elif r > 6:
            s = 65
        elif r > 2:
            s = 45
        elif r > 0:
            s = 30
        else:
            s = 15
        scores.append((s, weight))
    if not scores:
        return 50.0
    return round(sum(s * w for s, w in scores) / sum(w for _, w in scores), 1)


def _score_income(profile: dict) -> float:
    y = profile.get("dividend_yield")
    if y is None:
        return 30.0
    if y > 5:
        return 95
    if y > 3:
        return 85
    if y > 2:
        return 70
    if y > 1:
        return 50
    return 30


def _score_diversification(profile: dict, category: str | None) -> float:
    score = 50.0
    if category in _BROAD_CATEGORIES:
        score = 90
    elif category and category.startswith("sector_"):
        score = 40
    elif category in _NARROW_CATEGORIES:
        score = 25
    elif category in {"us_mid", "us_small", "reit", "bond_treasury",
                      "bond_corporate", "bond_muni", "bond_tips", "bond_intl",
                      "low_volatility"}:
        score = 65
    n_sectors = len(profile.get("sector_weights") or {})
    if n_sectors >= 8:
        score = min(100, score + 5)
    top = profile.get("top_holdings") or []
    if top:
        top_weight = sum(h.get("weight") or 0 for h in top[:10])
        if top_weight > 60:
            score -= 15  # heavily concentrated in a handful of names
    return max(0, min(100, score))


def _score_cost(profile: dict) -> float:
    er = profile.get("expense_ratio")
    if er is None:
        return 50.0
    if er <= 0.05:
        return 100
    if er <= 0.10:
        return 90
    if er <= 0.20:
        return 75
    if er <= 0.40:
        return 55
    if er <= 0.75:
        return 35
    return 15


def _risk_level(profile: dict) -> str:
    vol = profile.get("volatility_1y")
    if vol is None:
        return "Unknown"
    if vol < 10:
        return "Low"
    if vol < 18:
        return "Moderate"
    if vol < 28:
        return "High"
    return "Very High"


def score_etf(profile: dict, category: str | None = None) -> dict:
    """Score an ETF profile from fetch_etf_profile(). Returns sub-scores,
    weighted overall score, letter grade, and risk label."""
    weights = load_etf_weights()
    subs = {
        "safety": _score_safety(profile),
        "growth": _score_growth(profile),
        "income": _score_income(profile),
        "diversification": _score_diversification(profile, category),
        "cost": _score_cost(profile),
    }
    overall = round(sum(subs[k] * weights.get(k, 0) for k in subs), 1)
    return {
        "scores": subs,
        "overall": overall,
        "grade": score_to_grade(overall),
        "risk_level": _risk_level(profile),
    }
