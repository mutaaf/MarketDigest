"""Composite sentiment engine: VIX + DXY + F&G + news + technical breadth."""

from typing import Any

from textblob import TextBlob

from src.utils.logging_config import get_logger

logger = get_logger("sentiment")


def score_vix(vix_value: float | None) -> dict[str, Any]:
    """Score VIX component (0-100, higher = more greedy/complacent)."""
    if vix_value is None or vix_value == 0 or (isinstance(vix_value, float) and not (vix_value == vix_value)):
        return {"score": 50, "label": "N/A", "weight": 0}

    if vix_value > 30:
        score = max(0, 20 - (vix_value - 30))
    elif vix_value > 20:
        score = 20 + (30 - vix_value) * 3  # 20-50
    elif vix_value > 15:
        score = 50 + (20 - vix_value) * 6  # 50-80
    else:
        score = 80 + (15 - vix_value) * 4  # 80-100

    score = max(0, min(100, score))

    if vix_value < 15:
        label = "Complacent"
    elif vix_value < 20:
        label = "Normal"
    elif vix_value < 30:
        label = "Elevated Fear"
    else:
        label = "Panic"

    return {"score": round(score), "label": label, "weight": 25, "raw": vix_value}


def score_dxy(dxy_change_pct: float | None) -> dict[str, Any]:
    """Score DXY direction (0-100). Rising DXY = risk-off = lower score."""
    if dxy_change_pct is None:
        return {"score": 50, "label": "N/A", "weight": 0}

    # Invert: strong dollar = fear
    score = 50 - (dxy_change_pct * 15)
    score = max(0, min(100, score))

    if dxy_change_pct > 0.3:
        label = "Strong USD (Risk-Off)"
    elif dxy_change_pct > 0:
        label = "Mild USD Strength"
    elif dxy_change_pct > -0.3:
        label = "Mild USD Weakness"
    else:
        label = "Weak USD (Risk-On)"

    return {"score": round(score), "label": label, "weight": 15, "raw": dxy_change_pct}


def score_fear_greed(fg_data: dict | None) -> dict[str, Any]:
    """Score CNN Fear & Greed Index (already 0-100)."""
    if fg_data is None:
        return {"score": 50, "label": "N/A", "weight": 0}

    score = fg_data.get("score", 50)
    label = fg_data.get("classification", "Neutral")
    return {"score": round(score), "label": label, "weight": 30, "raw": score}


def score_news_sentiment(headlines: list[dict]) -> dict[str, Any]:
    """Score news sentiment using TextBlob polarity (0-100)."""
    if not headlines:
        return {"score": 50, "label": "N/A", "weight": 0}

    polarities = []
    for article in headlines:
        text = (article.get("title") or "") + " " + (article.get("description") or "")
        if text.strip():
            blob = TextBlob(text)
            polarities.append(blob.sentiment.polarity)

    if not polarities:
        return {"score": 50, "label": "Neutral", "weight": 0}

    avg_polarity = sum(polarities) / len(polarities)
    # Scale from [-1, 1] to [0, 100]
    score = (avg_polarity + 1) * 50
    score = max(0, min(100, score))

    if score > 65:
        label = "Positive"
    elif score > 55:
        label = "Slightly Positive"
    elif score > 45:
        label = "Neutral"
    elif score > 35:
        label = "Slightly Negative"
    else:
        label = "Negative"

    return {"score": round(score), "label": label, "weight": 15, "raw": round(avg_polarity, 3)}


def score_technical_breadth(analyses: list[dict]) -> dict[str, Any]:
    """Score based on how many instruments are in bullish vs bearish trends."""
    if not analyses:
        return {"score": 50, "label": "N/A", "weight": 0}

    bullish = sum(1 for a in analyses if a.get("trend", "").endswith("bullish"))
    bearish = sum(1 for a in analyses if a.get("trend", "").endswith("bearish"))
    total = len(analyses)

    if total == 0:
        return {"score": 50, "label": "N/A", "weight": 0}

    bullish_pct = bullish / total
    score = bullish_pct * 100
    score = max(0, min(100, score))

    if score > 65:
        label = "Broad Strength"
    elif score > 45:
        label = "Mixed"
    else:
        label = "Broad Weakness"

    return {
        "score": round(score),
        "label": label,
        "weight": 15,
        "raw": {"bullish": bullish, "bearish": bearish, "total": total},
    }


def compute_composite_sentiment(
    vix_value: float | None = None,
    dxy_change_pct: float | None = None,
    fg_data: dict | None = None,
    headlines: list[dict] | None = None,
    tech_analyses: list[dict] | None = None,
) -> dict[str, Any]:
    """Compute weighted composite sentiment score (0-100)."""
    components = {
        "vix": score_vix(vix_value),
        "dxy": score_dxy(dxy_change_pct),
        "fear_greed": score_fear_greed(fg_data),
        "news": score_news_sentiment(headlines or []),
        "technicals": score_technical_breadth(tech_analyses or []),
    }

    total_weight = sum(c["weight"] for c in components.values())
    if total_weight == 0:
        composite = 50
    else:
        composite = sum(c["score"] * c["weight"] for c in components.values()) / total_weight

    composite = round(max(0, min(100, composite)))

    if composite >= 75:
        overall = "Extreme Greed"
    elif composite >= 60:
        overall = "Greed"
    elif composite >= 45:
        overall = "Neutral"
    elif composite >= 25:
        overall = "Fear"
    else:
        overall = "Extreme Fear"

    return {
        "composite_score": composite,
        "classification": overall,
        "components": components,
    }


def get_sentiment_emoji(score: int) -> str:
    if score >= 75:
        return "🟢🟢"
    elif score >= 60:
        return "🟢"
    elif score >= 45:
        return "🟡"
    elif score >= 25:
        return "🔴"
    else:
        return "🔴🔴"
