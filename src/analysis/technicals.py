"""Technical analysis — RSI, SMA/EMA, support/resistance, trend detection."""

import numpy as np
import pandas as pd

from src.utils.logging_config import get_logger

logger = get_logger("technicals")


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Compute RSI from a price series."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()


def compute_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def compute_pivot_points(high: float, low: float, close: float) -> dict[str, float]:
    """Classic pivot points from previous day's HLC."""
    pivot = (high + low + close) / 3
    return {
        "pivot": round(pivot, 5),
        "r1": round(2 * pivot - low, 5),
        "r2": round(pivot + (high - low), 5),
        "s1": round(2 * pivot - high, 5),
        "s2": round(pivot - (high - low), 5),
    }


def detect_trend(series: pd.Series, short_period: int = 20, long_period: int = 50) -> str:
    """Detect trend using SMA crossover."""
    if len(series) < long_period:
        return "insufficient_data"

    sma_short = compute_sma(series, short_period).iloc[-1]
    sma_long = compute_sma(series, long_period).iloc[-1]
    price = series.iloc[-1]

    if price > sma_short > sma_long:
        return "bullish"
    elif price < sma_short < sma_long:
        return "bearish"
    elif sma_short > sma_long:
        return "weakly_bullish"
    elif sma_short < sma_long:
        return "weakly_bearish"
    return "neutral"


def find_support_resistance(df: pd.DataFrame, window: int = 5) -> dict[str, list[float]]:
    """Find support/resistance from recent swing highs/lows."""
    highs = df["High"]
    lows = df["Low"]

    resistances = []
    supports = []

    for i in range(window, len(df) - window):
        # Swing high
        if highs.iloc[i] == highs.iloc[i - window:i + window + 1].max():
            resistances.append(round(float(highs.iloc[i]), 4))
        # Swing low
        if lows.iloc[i] == lows.iloc[i - window:i + window + 1].min():
            supports.append(round(float(lows.iloc[i]), 4))

    # Deduplicate close levels (within 0.5%)
    resistances = _deduplicate_levels(sorted(resistances, reverse=True)[:5])
    supports = _deduplicate_levels(sorted(supports)[:5])

    return {"resistance": resistances, "support": supports}


def _deduplicate_levels(levels: list[float], threshold: float = 0.005) -> list[float]:
    """Remove levels that are too close to each other."""
    if not levels:
        return []
    result = [levels[0]]
    for lvl in levels[1:]:
        if all(abs(lvl - r) / max(r, 0.0001) > threshold for r in result):
            result.append(lvl)
    return result


def get_rsi_label(rsi: float) -> str:
    if rsi >= 70:
        return "Overbought"
    elif rsi >= 60:
        return "Bullish"
    elif rsi <= 30:
        return "Oversold"
    elif rsi <= 40:
        return "Bearish"
    return "Neutral"


def get_trend_emoji(trend: str) -> str:
    mapping = {
        "bullish": "📈",
        "weakly_bullish": "↗️",
        "bearish": "📉",
        "weakly_bearish": "↘️",
        "neutral": "➡️",
    }
    return mapping.get(trend, "❓")


def compute_atr(df: pd.DataFrame, period: int = 14) -> float | None:
    """Average True Range — volatility measure."""
    if df is None or len(df) < period + 1:
        return None
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean().iloc[-1]
    return round(float(atr), 5) if not np.isnan(atr) else None


def compute_weekly_pivots(df: pd.DataFrame) -> dict | None:
    """Classic pivot points from the last *completed* weekly bar.

    Resamples daily OHLCV to weekly, uses iloc[-2] (the last fully closed week)
    to avoid partial-week distortion. Returns the same structure as daily pivots
    plus week_high, week_low, week_close for context.
    """
    if df is None or len(df) < 10:
        return None
    try:
        weekly = df.resample("W").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last",
        }).dropna()
        if len(weekly) < 2:
            return None
        # Use the last *completed* week (iloc[-2]); iloc[-1] may be partial
        last_week = weekly.iloc[-2]
        h, l, c = float(last_week["High"]), float(last_week["Low"]), float(last_week["Close"])
        pivots = compute_pivot_points(h, l, c)
        pivots["week_high"] = round(h, 5)
        pivots["week_low"] = round(l, 5)
        pivots["week_close"] = round(c, 5)
        return pivots
    except Exception:
        return None


def compute_weekly_atr(df: pd.DataFrame, period: int = 14) -> float | None:
    """ATR on weekly-resampled bars for wider stop/target levels."""
    if df is None or len(df) < (period + 1) * 5:
        return None
    try:
        weekly = df.resample("W").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last",
        }).dropna()
        if len(weekly) < period + 1:
            return None
        high = weekly["High"]
        low = weekly["Low"]
        close = weekly["Close"]
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        atr = tr.ewm(span=period, adjust=False).mean().iloc[-1]
        return round(float(atr), 5) if not np.isnan(atr) else None
    except Exception:
        return None


def compute_gap_pct(df: pd.DataFrame) -> float | None:
    """Today's open vs yesterday's close as a percentage."""
    if df is None or len(df) < 2:
        return None
    today_open = float(df["Open"].iloc[-1])
    prev_close = float(df["Close"].iloc[-2])
    if prev_close == 0:
        return None
    gap = (today_open - prev_close) / prev_close * 100
    return round(gap, 3) if not np.isnan(gap) else None


def compute_volume_ratio(df: pd.DataFrame, lookback: int = 20) -> float | None:
    """Today's volume / N-day average volume."""
    if df is None or "Volume" not in df.columns or len(df) < lookback + 1:
        return None
    today_vol = float(df["Volume"].iloc[-1])
    avg_vol = float(df["Volume"].iloc[-(lookback + 1):-1].mean())
    if avg_vol == 0:
        return None
    ratio = today_vol / avg_vol
    return round(ratio, 2) if not np.isnan(ratio) else None


def full_analysis(df: pd.DataFrame, ticker: str = "") -> dict:
    """Run full technical analysis on OHLCV DataFrame."""
    if df is None or df.empty or len(df) < 14:
        return {"error": "insufficient_data", "ticker": ticker}

    close = df["Close"]
    rsi_series = compute_rsi(close)
    rsi_val = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50.0

    sma_20 = float(compute_sma(close, 20).iloc[-1]) if len(close) >= 20 else None
    sma_50 = float(compute_sma(close, 50).iloc[-1]) if len(close) >= 50 else None
    ema_12 = float(compute_ema(close, 12).iloc[-1])
    ema_26 = float(compute_ema(close, 26).iloc[-1]) if len(close) >= 26 else None

    trend = detect_trend(close)
    sr = find_support_resistance(df) if len(df) >= 15 else {"support": [], "resistance": []}

    prev_high = float(df["High"].iloc[-2]) if len(df) > 1 else None
    prev_low = float(df["Low"].iloc[-2]) if len(df) > 1 else None
    prev_close = float(close.iloc[-2]) if len(close) > 1 else None
    pivots = compute_pivot_points(prev_high, prev_low, prev_close) if prev_high else {}

    atr = compute_atr(df)
    gap_pct = compute_gap_pct(df)
    volume_ratio = compute_volume_ratio(df)

    return {
        "ticker": ticker,
        "rsi": round(rsi_val, 1),
        "rsi_label": get_rsi_label(rsi_val),
        "sma_20": round(sma_20, 4) if sma_20 else None,
        "sma_50": round(sma_50, 4) if sma_50 else None,
        "ema_12": round(ema_12, 4),
        "ema_26": round(ema_26, 4) if ema_26 else None,
        "trend": trend,
        "trend_emoji": get_trend_emoji(trend),
        "pivots": pivots,
        "support_resistance": sr,
        "atr": atr,
        "gap_pct": gap_pct,
        "volume_ratio": volume_ratio,
    }
