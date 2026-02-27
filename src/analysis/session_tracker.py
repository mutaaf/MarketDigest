"""Trading session tracker — Sydney/Tokyo/London/NY OHLC & performance."""

from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from src.utils.logging_config import get_logger
from src.utils.timezone import now_ct, session_times_utc

logger = get_logger("session_tracker")


def get_session_performance(
    intraday_df: pd.DataFrame,
    session_name: str,
    reference_date: datetime | None = None,
) -> dict[str, Any] | None:
    """Extract OHLC and performance for a specific trading session from intraday data."""
    if intraday_df is None or intraday_df.empty:
        return None

    try:
        open_utc, close_utc = session_times_utc(session_name, reference_date)
    except ValueError:
        return None

    # Filter data within session window
    df = intraday_df.copy()
    if df.index.tzinfo is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")

    mask = (df.index >= open_utc) & (df.index <= close_utc)
    session_data = df[mask]

    if session_data.empty:
        return None

    session_open = float(session_data["Open"].iloc[0])
    session_close = float(session_data["Close"].iloc[-1])
    session_high = float(session_data["High"].max())
    session_low = float(session_data["Low"].min())
    change = session_close - session_open
    change_pct = (change / session_open) * 100 if session_open else 0
    range_val = session_high - session_low

    return {
        "session": session_name,
        "open": round(session_open, 4),
        "high": round(session_high, 4),
        "low": round(session_low, 4),
        "close": round(session_close, 4),
        "change": round(change, 4),
        "change_pct": round(change_pct, 2),
        "range": round(range_val, 4),
    }


def get_overnight_recap(
    intraday_data: dict[str, pd.DataFrame],
    instrument_names: dict[str, str],
) -> dict[str, Any]:
    """Get Sydney and Tokyo session performance for overnight recap."""
    results = {"sydney": {}, "tokyo": {}}

    # Use previous day for overnight sessions (they happen evening before)
    yesterday = now_ct() - timedelta(days=1)

    for ticker, df in intraday_data.items():
        name = instrument_names.get(ticker, ticker)
        for session in ["sydney", "tokyo"]:
            perf = get_session_performance(df, session, yesterday)
            if perf:
                perf["name"] = name
                results[session][ticker] = perf

    return results


def get_session_levels(
    intraday_data: dict[str, pd.DataFrame],
    session_name: str,
    instrument_names: dict[str, str],
) -> dict[str, dict[str, Any]]:
    """Get session OHLC levels for all instruments."""
    results = {}
    for ticker, df in intraday_data.items():
        perf = get_session_performance(df, session_name)
        if perf:
            perf["name"] = instrument_names.get(ticker, ticker)
            results[ticker] = perf
    return results


def get_active_session() -> str | None:
    """Determine which session is currently active based on CT time."""
    now = now_ct()
    hour = now.hour
    minute = now.minute
    t = hour * 60 + minute

    # Session windows in CT minutes
    sessions = {
        "new_york": (7 * 60, 16 * 60),       # 7:00 AM - 4:00 PM
        "london": (2 * 60, 11 * 60),          # 2:00 AM - 11:00 AM
    }
    # Overnight sessions span midnight
    if t >= 16 * 60 or t < 1 * 60:
        return "sydney"
    if t >= 18 * 60 or t < 3 * 60:
        return "tokyo"

    for session, (start, end) in sessions.items():
        if start <= t <= end:
            return session

    return None
