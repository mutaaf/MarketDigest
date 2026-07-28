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
        h, lo, c = float(last_week["High"]), float(last_week["Low"]), float(last_week["Close"])
        pivots = compute_pivot_points(h, lo, c)
        pivots["week_high"] = round(h, 5)
        pivots["week_low"] = round(lo, 5)
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


def compute_monthly_pivots(df: pd.DataFrame) -> dict | None:
    """Classic pivot points from the last *completed* monthly bar.

    Resamples daily OHLCV to monthly, uses iloc[-2] (the last fully closed month)
    to avoid partial-month distortion.
    """
    if df is None or len(df) < 30:
        return None
    try:
        monthly = df.resample("ME").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last",
        }).dropna()
        if len(monthly) < 2:
            return None
        last_month = monthly.iloc[-2]
        h, lo, c = float(last_month["High"]), float(last_month["Low"]), float(last_month["Close"])
        pivots = compute_pivot_points(h, lo, c)
        pivots["month_high"] = round(h, 5)
        pivots["month_low"] = round(lo, 5)
        pivots["month_close"] = round(c, 5)
        return pivots
    except Exception:
        return None


def compute_monthly_atr(df: pd.DataFrame, period: int = 6) -> float | None:
    """ATR on monthly-resampled bars. Shorter period since monthly bars are sparse."""
    if df is None or len(df) < (period + 1) * 20:
        return None
    try:
        monthly = df.resample("ME").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last",
        }).dropna()
        if len(monthly) < period + 1:
            return None
        high = monthly["High"]
        low = monthly["Low"]
        close = monthly["Close"]
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


def weekly_full_analysis(df: pd.DataFrame, ticker: str = "") -> dict:
    """Full analysis on weekly-resampled data.

    Weekly RSI, weekly trend (SMA10w vs SMA20w), weekly pivots,
    weekly S/R, weekly ATR.
    """
    if df is None or df.empty or len(df) < 70:
        return {"error": "insufficient_data", "ticker": ticker}

    try:
        weekly = df.resample("W").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last",
        }).dropna()
        if len(weekly) < 14:
            return {"error": "insufficient_data", "ticker": ticker}

        close = weekly["Close"]
        rsi_series = compute_rsi(close)
        rsi_val = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50.0

        sma_10 = float(compute_sma(close, 10).iloc[-1]) if len(close) >= 10 else None
        sma_20 = float(compute_sma(close, 20).iloc[-1]) if len(close) >= 20 else None

        trend = detect_trend(close, short_period=10, long_period=20)
        sr = find_support_resistance(weekly, window=3) if len(weekly) >= 10 else {"support": [], "resistance": []}

        pivots = compute_weekly_pivots(df)
        atr = compute_weekly_atr(df)

        return {
            "ticker": ticker,
            "rsi": round(rsi_val, 1),
            "rsi_label": get_rsi_label(rsi_val),
            "sma_short": round(sma_10, 4) if sma_10 else None,
            "sma_long": round(sma_20, 4) if sma_20 else None,
            "trend": trend,
            "trend_emoji": get_trend_emoji(trend),
            "pivots": pivots or {},
            "support_resistance": sr,
            "atr": atr,
        }
    except Exception as e:
        logger.debug(f"weekly_full_analysis failed for {ticker}: {e}")
        return {"error": "analysis_failed", "ticker": ticker}


def monthly_full_analysis(df: pd.DataFrame, ticker: str = "") -> dict:
    """Full analysis on monthly-resampled data.

    Monthly RSI, monthly trend (SMA6m vs SMA12m), monthly pivots,
    monthly S/R, monthly ATR.
    Returns {"error": "insufficient_data"} if < 14 monthly bars.
    """
    if df is None or df.empty or len(df) < 300:
        return {"error": "insufficient_data", "ticker": ticker}

    try:
        monthly = df.resample("ME").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last",
        }).dropna()
        if len(monthly) < 14:
            return {"error": "insufficient_data", "ticker": ticker}

        close = monthly["Close"]
        rsi_series = compute_rsi(close)
        rsi_val = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50.0

        sma_6 = float(compute_sma(close, 6).iloc[-1]) if len(close) >= 6 else None
        sma_12 = float(compute_sma(close, 12).iloc[-1]) if len(close) >= 12 else None

        trend = detect_trend(close, short_period=6, long_period=12)
        sr = find_support_resistance(monthly, window=2) if len(monthly) >= 8 else {"support": [], "resistance": []}

        pivots = compute_monthly_pivots(df)
        atr = compute_monthly_atr(df)

        return {
            "ticker": ticker,
            "rsi": round(rsi_val, 1),
            "rsi_label": get_rsi_label(rsi_val),
            "sma_short": round(sma_6, 4) if sma_6 else None,
            "sma_long": round(sma_12, 4) if sma_12 else None,
            "trend": trend,
            "trend_emoji": get_trend_emoji(trend),
            "pivots": pivots or {},
            "support_resistance": sr,
            "atr": atr,
        }
    except Exception as e:
        logger.debug(f"monthly_full_analysis failed for {ticker}: {e}")
        return {"error": "analysis_failed", "ticker": ticker}


def compute_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3,
                       smooth: int = 3) -> dict[str, float] | None:
    """Stochastic Oscillator (%K and %D)."""
    if df is None or len(df) < k_period + d_period:
        return None
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()

    denom = highest_high - lowest_low
    denom = denom.replace(0, np.nan)
    fast_k = 100 * (close - lowest_low) / denom
    k = fast_k.rolling(window=smooth).mean()
    d = k.rolling(window=d_period).mean()

    k_val = float(k.iloc[-1]) if not np.isnan(k.iloc[-1]) else None
    d_val = float(d.iloc[-1]) if not np.isnan(d.iloc[-1]) else None
    if k_val is None:
        return None
    return {"k": round(k_val, 1), "d": round(d_val, 1) if d_val else None}


def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26,
                 signal: int = 9) -> dict[str, float] | None:
    """MACD line, signal line, and histogram."""
    if len(series) < slow + signal:
        return None
    ema_fast = compute_ema(series, fast)
    ema_slow = compute_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = compute_ema(macd_line, signal)
    histogram = macd_line - signal_line

    m = float(macd_line.iloc[-1])
    s = float(signal_line.iloc[-1])
    h = float(histogram.iloc[-1])
    if np.isnan(m):
        return None
    return {
        "macd": round(m, 5),
        "signal": round(s, 5),
        "histogram": round(h, 5),
        "crossover": h > 0 and float(histogram.iloc[-2]) <= 0 if len(histogram) > 1 else False,
        "crossunder": h < 0 and float(histogram.iloc[-2]) >= 0 if len(histogram) > 1 else False,
    }


def compute_bollinger_bands(series: pd.Series, period: int = 20,
                            std_dev: float = 2.0) -> dict[str, float] | None:
    """Bollinger Bands — upper, middle, lower, %B, bandwidth."""
    if len(series) < period:
        return None
    middle = compute_sma(series, period)
    rolling_std = series.rolling(window=period).std()
    upper = middle + std_dev * rolling_std
    lower = middle - std_dev * rolling_std

    mid = float(middle.iloc[-1])
    up = float(upper.iloc[-1])
    lo = float(lower.iloc[-1])
    price = float(series.iloc[-1])

    if np.isnan(mid) or up == lo:
        return None

    pct_b = (price - lo) / (up - lo)  # 0 = lower band, 1 = upper band
    bandwidth = (up - lo) / mid * 100

    return {
        "upper": round(up, 5),
        "middle": round(mid, 5),
        "lower": round(lo, 5),
        "pct_b": round(pct_b, 3),
        "bandwidth": round(bandwidth, 2),
        "squeeze": bandwidth < 4.0,  # low volatility squeeze
    }


def detect_ema_crossover(series: pd.Series, fast: int = 9, slow: int = 21) -> dict:
    """Detect EMA crossover/crossunder events."""
    if len(series) < slow + 2:
        return {"signal": "none", "fast_ema": None, "slow_ema": None}
    ema_f = compute_ema(series, fast)
    ema_s = compute_ema(series, slow)

    curr_diff = float(ema_f.iloc[-1] - ema_s.iloc[-1])
    prev_diff = float(ema_f.iloc[-2] - ema_s.iloc[-2])

    signal = "none"
    if curr_diff > 0 and prev_diff <= 0:
        signal = "bullish_cross"
    elif curr_diff < 0 and prev_diff >= 0:
        signal = "bearish_cross"
    elif curr_diff > 0:
        signal = "bullish"
    elif curr_diff < 0:
        signal = "bearish"

    return {
        "signal": signal,
        "fast_ema": round(float(ema_f.iloc[-1]), 5),
        "slow_ema": round(float(ema_s.iloc[-1]), 5),
    }


def compute_adx(df: pd.DataFrame, period: int = 14) -> float | None:
    """Average Directional Index — measures trend strength (0-100).
    ADX > 25 = trending, ADX < 20 = ranging.
    """
    if df is None or len(df) < period * 2:
        return None
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    plus_dm = high.diff().copy()
    minus_dm = -low.diff().copy()

    # Only keep positive directional movement
    plus_dm[(plus_dm < 0) | (plus_dm < minus_dm)] = 0
    minus_dm[(minus_dm < 0) | (minus_dm < plus_dm)] = 0

    # True Range
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    atr = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(span=period, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(span=period, adjust=False).mean() / atr

    di_sum = plus_di + minus_di
    di_sum = di_sum.replace(0, np.nan)
    dx = (plus_di - minus_di).abs() / di_sum * 100
    adx = dx.ewm(span=period, adjust=False).mean()

    val = float(adx.iloc[-1])
    return round(val, 1) if not np.isnan(val) else None


def compute_donchian(df: pd.DataFrame, period: int = 20) -> dict | None:
    """Donchian Channel — highest high and lowest low of N periods."""
    if df is None or len(df) < period:
        return None
    upper = float(df["High"].rolling(period).max().iloc[-1])
    lower = float(df["Low"].rolling(period).min().iloc[-1])
    mid = (upper + lower) / 2
    return {"upper": round(upper, 5), "lower": round(lower, 5), "middle": round(mid, 5)}


def compute_donchian_exit(df: pd.DataFrame, period: int = 10) -> dict | None:
    """Shorter Donchian for trailing stop (Turtle exit)."""
    return compute_donchian(df, period)


def detect_reversal_candle(df: pd.DataFrame) -> dict:
    """Detect bullish/bearish reversal candles on the latest bar."""
    if df is None or len(df) < 2:
        return {"bullish": False, "bearish": False}

    o = float(df["Open"].iloc[-1])
    h = float(df["High"].iloc[-1])
    lo = float(df["Low"].iloc[-1])
    c = float(df["Close"].iloc[-1])
    bar_range = h - lo

    if bar_range == 0:
        return {"bullish": False, "bearish": False}

    body_pct = abs(c - o) / bar_range
    close_position = (c - lo) / bar_range  # 0 = closed at low, 1 = closed at high

    # Bullish: close > open AND close in upper 60% of range
    bullish = c > o and close_position >= 0.6
    # Bearish: close < open AND close in lower 40% of range
    bearish = c < o and close_position <= 0.4

    # Hammer (long lower wick, small body at top)
    lower_wick = (min(o, c) - lo) / bar_range
    hammer = lower_wick >= 0.6 and close_position >= 0.6

    # Shooting star (long upper wick, small body at bottom)
    upper_wick = (h - max(o, c)) / bar_range
    shooting_star = upper_wick >= 0.6 and close_position <= 0.4

    return {
        "bullish": bullish or hammer,
        "bearish": bearish or shooting_star,
        "hammer": hammer,
        "shooting_star": shooting_star,
        "close_position": round(close_position, 2),
    }


def detect_inside_day(df: pd.DataFrame) -> bool:
    """Detect if yesterday was an inside day (range within prior day's range)."""
    if df is None or len(df) < 3:
        return False
    # Yesterday's range inside day-before-yesterday's range
    h1 = float(df["High"].iloc[-2])
    l1 = float(df["Low"].iloc[-2])
    h0 = float(df["High"].iloc[-3])
    l0 = float(df["Low"].iloc[-3])
    return h1 < h0 and l1 > l0


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
