"""Market regime detection — classifies current market conditions."""

import pandas as pd

from src.analysis.technicals import (
    compute_adx,
    compute_bollinger_bands,
    compute_ema,
)
from src.signals.strategies.base import MarketRegime
from src.utils.logging_config import get_logger

logger = get_logger("regime")


def detect_regime(df: pd.DataFrame, config: dict | None = None) -> MarketRegime:
    """Classify current market regime using ADX, BB bandwidth, and EMA slope.

    Returns MarketRegime enum.
    """
    if df is None or len(df) < 60:
        return MarketRegime.RANGING  # Default if insufficient data

    cfg = config or {}
    adx_trending = cfg.get("adx_trending", 25)
    adx_ranging = cfg.get("adx_ranging", 20)
    bb_squeeze_pctile = cfg.get("bb_squeeze_percentile", 20)

    close = df["Close"]
    price = float(close.iloc[-1])

    # ADX — trend strength
    adx = compute_adx(df, 14)
    if adx is None:
        adx = 20  # Assume ranging if can't compute

    # EMA 50 — trend direction and slope
    ema50 = compute_ema(close, 50)
    ema50_val = float(ema50.iloc[-1])
    above_ema = price > ema50_val

    # EMA slope over last 5 bars (% change)
    if len(ema50) >= 6:
        ema50_slope = (float(ema50.iloc[-1]) - float(ema50.iloc[-6])) / float(ema50.iloc[-6]) * 100
    else:
        ema50_slope = 0

    # BB bandwidth percentile for squeeze detection
    bb = compute_bollinger_bands(close, 20, 2.0)
    if bb:
        bandwidth = bb["bandwidth"]
        # Compute bandwidth percentile over last 100 bars
        bb_series = []
        for i in range(max(20, len(close) - 100), len(close)):
            b = compute_bollinger_bands(close.iloc[:i + 1], 20, 2.0)
            if b:
                bb_series.append(b["bandwidth"])
        if bb_series:
            percentile = sum(1 for b in bb_series if b <= bandwidth) / len(bb_series) * 100
        else:
            percentile = 50
    else:
        bandwidth = 5.0
        percentile = 50

    # Classification
    if adx >= adx_trending:
        if above_ema and ema50_slope > 0.1:
            regime = MarketRegime.TRENDING_UP
        elif not above_ema and ema50_slope < -0.1:
            regime = MarketRegime.TRENDING_DOWN
        else:
            regime = MarketRegime.VOLATILE
    elif adx <= adx_ranging:
        if percentile <= bb_squeeze_pctile:
            regime = MarketRegime.LOW_VOLATILITY
        else:
            regime = MarketRegime.RANGING
    else:
        # ADX between ranging and trending thresholds
        if percentile <= bb_squeeze_pctile:
            regime = MarketRegime.LOW_VOLATILITY
        else:
            regime = MarketRegime.RANGING

    logger.debug(f"Regime: {regime.value} | ADX={adx} | EMA50 slope={ema50_slope:.2f}% | "
                 f"BB bandwidth={bandwidth:.1f} (pctile={percentile:.0f}%)")
    return regime


def get_regime_info(df: pd.DataFrame, config: dict | None = None) -> dict:
    """Get regime with diagnostic info for display."""
    regime = detect_regime(df, config)
    adx = compute_adx(df, 14)
    close = df["Close"]
    ema50 = compute_ema(close, 50)
    bb = compute_bollinger_bands(close, 20, 2.0)

    return {
        "regime": regime.value,
        "adx": adx,
        "ema50": round(float(ema50.iloc[-1]), 5) if ema50 is not None and len(ema50) > 0 else None,
        "bb_bandwidth": bb["bandwidth"] if bb else None,
        "description": {
            "trending_up": "Strong uptrend — favor buying pullbacks",
            "trending_down": "Strong downtrend — favor selling rallies",
            "ranging": "Sideways market — mean reversion at extremes",
            "volatile": "High volatility, no clear direction — breakouts possible",
            "low_vol": "Squeeze/compression — expect a breakout soon",
        }.get(regime.value, ""),
    }
