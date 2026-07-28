"""Confluence scoring — multi-indicator agreement scoring with 2:1 R/R enforcement."""

import yaml
from pathlib import Path

from src.analysis.daytrade_scorer import score_to_grade
from src.utils.logging_config import get_logger

logger = get_logger("confluence")

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "signals.yaml"


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def score_ema_cross(ema_data: dict) -> float:
    """Score EMA crossover signal (0-100)."""
    sig = ema_data.get("signal", "none")
    return {
        "bullish_cross": 100,  # Fresh crossover = strongest
        "bearish_cross": 100,  # Fresh crossunder for shorts
        "bullish": 65,
        "bearish": 65,
        "none": 30,
    }.get(sig, 30)


def score_rsi(rsi: float | None, direction: str) -> float:
    """Score RSI for signal quality (0-100)."""
    if rsi is None:
        return 40
    if direction == "BUY":
        if 30 <= rsi <= 45:
            return 95  # Oversold recovery = prime buy zone
        if 45 < rsi <= 55:
            return 70  # Neutral, ok
        if rsi < 30:
            return 80  # Deeply oversold, bounce potential
        if rsi > 70:
            return 10  # Overbought, bad for buys
        return 50
    else:  # SELL
        if 55 <= rsi <= 70:
            return 95  # Overbought reversal zone
        if 45 <= rsi < 55:
            return 70
        if rsi > 70:
            return 80  # Deeply overbought
        if rsi < 30:
            return 10  # Oversold, bad for sells
        return 50


def score_bollinger(bb_data: dict | None, direction: str) -> float:
    """Score Bollinger Band position (0-100)."""
    if not bb_data:
        return 40
    pct_b = bb_data.get("pct_b", 0.5)
    squeeze = bb_data.get("squeeze", False)

    if direction == "BUY":
        if pct_b <= 0.1:
            return 95  # At lower band = strong buy
        if pct_b <= 0.3:
            return 80
        if squeeze and pct_b < 0.5:
            return 85  # Squeeze + lower half = breakout buy
        if pct_b >= 0.9:
            return 15  # At upper band = bad buy
        return 50
    else:  # SELL
        if pct_b >= 0.9:
            return 95  # At upper band = strong sell
        if pct_b >= 0.7:
            return 80
        if squeeze and pct_b > 0.5:
            return 85
        if pct_b <= 0.1:
            return 15
        return 50


def score_stochastic(stoch_data: dict | None, direction: str) -> float:
    """Score Stochastic Oscillator (0-100)."""
    if not stoch_data:
        return 40
    k = stoch_data.get("k", 50)
    d = stoch_data.get("d", 50)
    if d is None:
        d = k

    if direction == "BUY":
        if k < 20 and k > d:
            return 95  # Oversold + K crossing above D
        if k < 30:
            return 75
        if k > 80:
            return 15  # Overbought
        return 50
    else:  # SELL
        if k > 80 and k < d:
            return 95  # Overbought + K crossing below D
        if k > 70:
            return 75
        if k < 20:
            return 15
        return 50


def score_macd(macd_data: dict | None, direction: str) -> float:
    """Score MACD confirmation (0-100)."""
    if not macd_data:
        return 40
    hist = macd_data.get("histogram", 0)

    if direction == "BUY":
        if macd_data.get("crossover"):
            return 100  # Bullish crossover
        if hist > 0:
            return 70
        return 25
    else:  # SELL
        if macd_data.get("crossunder"):
            return 100  # Bearish crossunder
        if hist < 0:
            return 70
        return 25


def score_pivot_proximity(price: float, pivots: dict, direction: str,
                          atr: float | None) -> float:
    """Score based on proximity to pivot levels (0-100)."""
    if not pivots or not price or price <= 0:
        return 40
    s1 = pivots.get("s1")
    r1 = pivots.get("r1")
    s2 = pivots.get("s2")
    r2 = pivots.get("r2")
    if s1 is None or r1 is None:
        return 40

    threshold = (atr or price * 0.01) * 0.5

    if direction == "BUY":
        if abs(price - s1) <= threshold:
            return 95  # Bouncing off S1
        if s2 and abs(price - s2) <= threshold:
            return 90  # At S2 even better
        if price > r1 and (price - r1) <= threshold:
            return 80  # Breaking R1 = momentum
        return 40
    else:  # SELL
        if abs(price - r1) <= threshold:
            return 95  # Rejected at R1
        if r2 and abs(price - r2) <= threshold:
            return 90
        if price < s1 and (s1 - price) <= threshold:
            return 80  # Breaking S1 = momentum short
        return 40


def score_atr_filter(atr: float | None, price: float) -> float:
    """ATR volatility filter — need enough movement for 2:1 R/R (0-100)."""
    if atr is None or price <= 0:
        return 40
    atr_pct = (atr / price) * 100
    if atr_pct >= 2.0:
        return 100
    if atr_pct >= 1.5:
        return 80
    if atr_pct >= 1.0:
        return 60
    if atr_pct >= 0.5:
        return 40
    return 15  # Too low volatility for profitable signals


def score_iv_rank(iv_rank: float | None, direction: str) -> float:
    """Score IV Rank for options signals (0-100)."""
    if iv_rank is None:
        return 40
    # High IV = good for selling premium, low IV = good for buying
    if direction == "BUY":
        if iv_rank < 20:
            return 90  # Cheap options
        if iv_rank < 40:
            return 70
        if iv_rank > 70:
            return 25  # Expensive, bad for buying
        return 50
    else:  # SELL
        if iv_rank > 70:
            return 90  # Rich premium
        if iv_rank > 50:
            return 70
        if iv_rank < 20:
            return 25
        return 50


def compute_confluence(
    price: float,
    direction: str,
    indicators: dict,
    asset_type: str = "forex",
) -> tuple[float, str, dict]:
    """Compute weighted confluence score.

    Returns:
        (score, grade, component_scores)
    """
    config = _load_config()
    weights = config.get(f"{asset_type}_weights", config.get("forex_weights"))

    components = {}

    # EMA crossover
    ema_data = indicators.get("ema_cross", {})
    components["ema_cross"] = score_ema_cross(ema_data)

    # RSI
    components["rsi"] = score_rsi(indicators.get("rsi"), direction)

    # Bollinger Bands
    components["bollinger"] = score_bollinger(indicators.get("bollinger"), direction)

    # Asset-specific indicators
    if asset_type == "forex":
        components["stochastic"] = score_stochastic(indicators.get("stochastic"), direction)
        components["macd"] = score_macd(indicators.get("macd"), direction)
    else:  # options/equity
        components["iv_rank"] = score_iv_rank(indicators.get("iv_rank"), direction)
        components["greeks"] = 50  # Placeholder until Tastytrade integration

    # Pivot proximity
    components["pivot"] = score_pivot_proximity(
        price, indicators.get("pivots", {}), direction,
        indicators.get("atr")
    )

    # ATR filter
    components["atr_filter"] = score_atr_filter(indicators.get("atr"), price)

    # Weighted composite
    score = sum(components.get(k, 40) * w for k, w in weights.items())
    score = round(score, 1)
    grade = score_to_grade(score)

    return score, grade, components
