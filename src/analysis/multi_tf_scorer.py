"""Multi-timeframe scoring — swing (weekly) and long-term (monthly) instrument scoring."""

from src.analysis.daytrade_scorer import score_to_grade
from src.utils.logging_config import get_logger

logger = get_logger("multi_tf_scorer")

# Default weights (overridable via config/scoring.yaml)
DEFAULT_SWING_WEIGHTS = {"rsi": 0.25, "trend": 0.30, "pivot": 0.25, "atr": 0.20}
DEFAULT_LT_WEIGHTS_EQUITY = {"rsi": 0.10, "trend": 0.15, "pivot": 0.10, "atr": 0.05, "fundamentals": 0.60}
DEFAULT_LT_WEIGHTS_NON_EQUITY = {"rsi": 0.25, "trend": 0.35, "pivot": 0.25, "atr": 0.15}


def _score_rsi_swing(rsi: float | None) -> float:
    """RSI score for swing timeframe. Sweet spot is mean-reversion zones."""
    if rsi is None:
        return 40
    if 30 <= rsi <= 45:
        return 90
    if 45 < rsi <= 55:
        return 70
    if 55 < rsi <= 65:
        return 50
    if rsi < 30:
        return 75  # oversold bounce
    if rsi > 70:
        return 20
    return 40


def _score_trend_swing(trend: str | None) -> float:
    """Trend alignment score for swing timeframe."""
    mapping = {
        "bullish": 100,
        "weakly_bullish": 80,
        "neutral": 40,
        "weakly_bearish": 20,
        "bearish": 0,
    }
    return mapping.get(trend or "neutral", 40)


def _score_pivot_swing(price: float, pivots: dict, atr: float | None) -> float:
    """Pivot proximity score using weekly pivots."""
    if not pivots or not price or price <= 0:
        return 40
    s1 = pivots.get("s1")
    r1 = pivots.get("r1")
    if s1 is None or r1 is None:
        return 40

    threshold = (atr or price * 0.02) * 0.5

    if s1 > 0 and abs(price - s1) <= threshold:
        return 90
    if r1 > 0 and price > r1 and (price - r1) <= threshold:
        return 85
    return 40


def _score_atr_swing(atr: float | None, price: float) -> float:
    """ATR volatility score for swing. Moderate volatility preferred."""
    if atr is None or price <= 0:
        return 40
    atr_pct = (atr / price) * 100
    if 3.0 <= atr_pct <= 8.0:
        return 90
    if 2.0 <= atr_pct < 3.0 or 8.0 < atr_pct <= 12.0:
        return 70
    if 1.0 <= atr_pct < 2.0:
        return 50
    if atr_pct > 12.0:
        return 40
    return 30


def score_instrument_swing(ta_weekly: dict, price_data: dict, weights: dict | None = None) -> dict | None:
    """Score instrument for swing trading (1-2 week horizon) using weekly technicals.

    Args:
        ta_weekly: Weekly technical analysis from weekly_full_analysis().
        price_data: Price dict with price, name, etc.
        weights: Optional explicit scoring weights.

    Returns:
        Dict with score, grade, signals, verdict, entry/target/stop, or None.
    """
    if ta_weekly.get("error") or not price_data:
        return None

    price = price_data.get("price")
    if not price or price <= 0:
        return None

    rsi = ta_weekly.get("rsi")
    trend = ta_weekly.get("trend")
    pivots = ta_weekly.get("pivots", {})
    atr = ta_weekly.get("atr")

    if weights is None:
        try:
            from src.retrace.scoring_config import load_swing_weights
            weights = load_swing_weights()
        except Exception:
            weights = dict(DEFAULT_SWING_WEIGHTS)

    scores = {
        "rsi": _score_rsi_swing(rsi),
        "trend": _score_trend_swing(trend),
        "pivot": _score_pivot_swing(price, pivots, atr),
        "atr": _score_atr_swing(atr, price),
    }
    composite = sum(scores[k] * weights.get(k, 0) for k in scores)

    # Entry / target / stop from weekly levels
    w_r1 = pivots.get("r1", price * 1.02)
    w_s1 = pivots.get("s1", price * 0.98)
    atr_val = atr or price * 0.02

    entry = price
    target = max(w_r1, price + atr_val)
    stop = max(w_s1, price - 0.5 * atr_val)

    target_level = "Weekly R1" if target == w_r1 else "Weekly ATR"
    stop_level = "Weekly S1" if stop == w_s1 else "Weekly ATR"

    risk = entry - stop
    reward = target - entry
    risk_reward = round(reward / risk, 2) if risk > 0 else 0.0

    rounded_score = round(composite, 1)
    signals = _build_swing_signals(ta_weekly, price)

    return {
        "timeframe": "swing",
        "score": rounded_score,
        "grade": score_to_grade(rounded_score),
        "signals": signals,
        "verdict": _build_tf_verdict(rounded_score, trend, signals, "Swing"),
        "entry": round(entry, 2),
        "target": round(target, 2),
        "stop": round(stop, 2),
        "target_level": target_level,
        "stop_level": stop_level,
        "risk_reward": risk_reward,
        "component_scores": scores,
    }


def _build_swing_signals(ta: dict, price: float) -> list[str]:
    """Build signal list for swing timeframe."""
    signals = []
    rsi = ta.get("rsi")
    trend = ta.get("trend")
    pivots = ta.get("pivots", {})

    if rsi is not None:
        if 30 <= rsi <= 45:
            signals.append(f"Weekly RSI recovery ({rsi:.0f})")
        elif rsi < 30:
            signals.append(f"Weekly oversold ({rsi:.0f})")
        elif rsi > 70:
            signals.append(f"Weekly overbought ({rsi:.0f})")

    if trend in ("bullish", "weakly_bullish"):
        signals.append(f"Weekly trend: {trend.replace('_', ' ')}")

    r1 = pivots.get("r1")
    s1 = pivots.get("s1")
    if r1 and price > r1:
        signals.append("Above weekly R1")
    elif s1 and price and abs(price - s1) / max(price, 0.01) < 0.01:
        signals.append("Near weekly S1")

    return signals[:3]


# ── Long-term scorer ──────────────────────────────────────────


def _score_rsi_longterm(rsi: float | None) -> float:
    """RSI score for long-term timeframe."""
    if rsi is None:
        return 40
    if 35 <= rsi <= 55:
        return 80
    if 55 < rsi <= 65:
        return 60
    if rsi < 30:
        return 85  # deep value
    if rsi > 70:
        return 25
    return 50


def _score_trend_longterm(trend: str | None) -> float:
    """Trend score for long-term. Strong trends heavily favored."""
    mapping = {
        "bullish": 100,
        "weakly_bullish": 75,
        "neutral": 45,
        "weakly_bearish": 20,
        "bearish": 0,
    }
    return mapping.get(trend or "neutral", 45)


def _score_pivot_longterm(price: float, pivots: dict, atr: float | None) -> float:
    """Pivot proximity score using monthly pivots."""
    if not pivots or not price or price <= 0:
        return 40
    s1 = pivots.get("s1")
    r1 = pivots.get("r1")
    if s1 is None or r1 is None:
        return 40

    threshold = (atr or price * 0.05) * 0.5

    if s1 > 0 and abs(price - s1) <= threshold:
        return 90
    if r1 > 0 and price > r1 and (price - r1) <= threshold:
        return 80
    return 40


def _score_atr_longterm(atr: float | None, price: float) -> float:
    """ATR for long-term. Lower volatility slightly preferred for stability."""
    if atr is None or price <= 0:
        return 40
    atr_pct = (atr / price) * 100
    if 5.0 <= atr_pct <= 15.0:
        return 80
    if 3.0 <= atr_pct < 5.0:
        return 70
    if 15.0 < atr_pct <= 25.0:
        return 50
    if atr_pct < 3.0:
        return 60
    return 30


def score_instrument_longterm(
    ta_monthly: dict,
    price_data: dict,
    fundamentals: dict | None = None,
    is_equity: bool = True,
    weights: dict | None = None,
) -> dict | None:
    """Score instrument for long-term investing (1-3 month horizon).

    Equity: 60% fundamentals + 40% monthly technicals.
    Non-equity: 100% monthly technicals.

    Args:
        ta_monthly: Monthly technical analysis from monthly_full_analysis().
        price_data: Price dict with price, name, etc.
        fundamentals: Fundamental scores dict (from score_fundamentals).
        is_equity: Whether this is a stock.
        weights: Optional explicit scoring weights.

    Returns:
        Dict with score, grade, signals, verdict, entry/target/stop, or None.
    """
    if ta_monthly.get("error") or not price_data:
        return None

    price = price_data.get("price")
    if not price or price <= 0:
        return None

    rsi = ta_monthly.get("rsi")
    trend = ta_monthly.get("trend")
    pivots = ta_monthly.get("pivots", {})
    atr = ta_monthly.get("atr")

    if weights is None:
        try:
            from src.retrace.scoring_config import load_longterm_weights
            weights = load_longterm_weights(is_equity)
        except Exception:
            weights = dict(DEFAULT_LT_WEIGHTS_EQUITY if is_equity else DEFAULT_LT_WEIGHTS_NON_EQUITY)

    scores = {
        "rsi": _score_rsi_longterm(rsi),
        "trend": _score_trend_longterm(trend),
        "pivot": _score_pivot_longterm(price, pivots, atr),
        "atr": _score_atr_longterm(atr, price),
    }

    if is_equity and fundamentals:
        scores["fundamentals"] = fundamentals.get("composite", 50)
    elif is_equity:
        scores["fundamentals"] = 50  # neutral if no data

    # For non-equity, fundamentals key won't be in weights
    composite = sum(scores.get(k, 50) * w for k, w in weights.items())

    # Entry / target / stop from monthly levels
    m_r1 = pivots.get("r1", price * 1.05)
    m_s1 = pivots.get("s1", price * 0.95)
    atr_val = atr or price * 0.05

    entry = price
    target = max(m_r1, price + atr_val)
    stop = max(m_s1, price - 0.5 * atr_val)

    target_level = "Monthly R1" if target == m_r1 else "Monthly ATR"
    stop_level = "Monthly S1" if stop == m_s1 else "Monthly ATR"

    risk = entry - stop
    reward = target - entry
    risk_reward = round(reward / risk, 2) if risk > 0 else 0.0

    rounded_score = round(composite, 1)
    signals = _build_longterm_signals(ta_monthly, price, fundamentals, is_equity)

    return {
        "timeframe": "longterm",
        "score": rounded_score,
        "grade": score_to_grade(rounded_score),
        "signals": signals,
        "verdict": _build_tf_verdict(rounded_score, trend, signals, "Long Term"),
        "entry": round(entry, 2),
        "target": round(target, 2),
        "stop": round(stop, 2),
        "target_level": target_level,
        "stop_level": stop_level,
        "risk_reward": risk_reward,
        "component_scores": scores,
    }


def _build_longterm_signals(ta: dict, price: float, fundamentals: dict | None, is_equity: bool) -> list[str]:
    """Build signal list for long-term timeframe."""
    signals = []
    rsi = ta.get("rsi")
    trend = ta.get("trend")

    if rsi is not None:
        if rsi < 35:
            signals.append(f"Monthly oversold ({rsi:.0f})")
        elif rsi > 65:
            signals.append(f"Monthly overbought ({rsi:.0f})")

    if trend in ("bullish", "weakly_bullish"):
        signals.append(f"Monthly trend: {trend.replace('_', ' ')}")
    elif trend in ("bearish", "weakly_bearish"):
        signals.append("Monthly downtrend")

    if is_equity and fundamentals:
        composite = fundamentals.get("composite", 50)
        if composite >= 75:
            signals.append("Strong fundamentals")
        elif composite <= 35:
            signals.append("Weak fundamentals")

    return signals[:3]


def _build_tf_verdict(score: float, trend: str | None, signals: list[str], timeframe_label: str) -> str:
    """Build verdict string for a timeframe."""
    top_signal = signals[0] if signals else "no clear catalyst"
    trend_label = (trend or "neutral").replace("_", " ")

    if score >= 80:
        return f"{timeframe_label}: Strong — {trend_label} trend, {top_signal}"
    if score >= 65:
        return f"{timeframe_label}: Solid — {top_signal}"
    if score >= 50:
        return f"{timeframe_label}: Neutral — waiting for clearer signals"
    if score >= 40:
        return f"{timeframe_label}: Weak — limited opportunity"
    return f"{timeframe_label}: Avoid — {top_signal}"
