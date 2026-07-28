"""ETF reference data — expense ratio, yield, AUM, holdings, returns, volatility.

yfinance-backed, cached 24h with stale fallback. All fields are best-effort:
a missing metric is None, never an exception.
"""

import math

from src.cache.manager import CacheManager
from src.utils.logging_config import get_logger

logger = get_logger("etf_data")

_cache = CacheManager()
_CACHE_TTL = 24 * 60 * 60  # 24 hours


def fetch_etf_profile(symbol: str, yf_symbol: str | None = None) -> dict | None:
    """Full ETF profile. Returns cached (or stale-cached) data when live fetch fails."""
    yf_symbol = yf_symbol or symbol
    cache_key = f"etf_profile:{symbol}"
    cached = _cache.get(cache_key, max_age_seconds=_CACHE_TTL)
    if cached is not None:
        return cached

    profile = _fetch_live(symbol, yf_symbol)
    if profile is not None:
        _cache.set(cache_key, profile)
        return profile

    stale = _cache.get_stale(cache_key)
    if stale is not None:
        logger.warning(f"ETF fetch failed for {symbol}; serving stale cache")
        stale["stale"] = True
    return stale


def _fetch_live(symbol: str, yf_symbol: str) -> dict | None:
    try:
        import yfinance as yf
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info or {}
        if not info.get("longName") and not info.get("shortName"):
            return None

        profile = {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName"),
            "fund_category": info.get("category"),
            "fund_family": info.get("fundFamily"),
            "expense_ratio": _expense_ratio(info),
            "dividend_yield": _dividend_yield(info),
            "aum": _num(info.get("totalAssets")),
            "beta_3y": _num(info.get("beta3Year")),
            "price": _num(info.get("regularMarketPrice") or info.get("previousClose")),
            "inception": info.get("fundInceptionDate"),
        }

        profile.update(_returns_and_volatility(ticker))
        profile.update(_holdings(ticker))
        return profile
    except Exception as e:
        logger.debug(f"ETF profile fetch failed for {yf_symbol}: {e}")
        return None


def _expense_ratio(info: dict) -> float | None:
    """Expense ratio in percent (0.03 means 0.03%/yr)."""
    for key in ("netExpenseRatio", "annualReportExpenseRatio"):
        val = _num(info.get(key))
        if val is not None:
            # yfinance has shipped both fraction (0.0003) and percent (0.03) forms
            return round(val * 100, 4) if val < 0.005 else round(val, 4)
    return None


def _dividend_yield(info: dict) -> float | None:
    """Trailing yield in percent."""
    val = _num(info.get("dividendYield"))
    if val is None:
        val = _num(info.get("trailingAnnualDividendYield"))
        if val is not None:
            val = val * 100
    elif val < 0.5:  # fraction form from older yfinance versions
        val = val * 100
    return round(val, 2) if val is not None else None


def _returns_and_volatility(ticker) -> dict:
    """Annualized total returns over 1/3/5/10y + 1y daily volatility, from history."""
    out = {"return_1y": None, "return_3y": None, "return_5y": None,
           "return_10y": None, "volatility_1y": None}
    try:
        import pandas as pd
        hist = ticker.history(period="10y", interval="1d", auto_adjust=True)
        if hist is None or hist.empty:
            return out
        close = hist["Close"].dropna()
        last = float(close.iloc[-1])

        for years, key in [(1, "return_1y"), (3, "return_3y"), (5, "return_5y"), (10, "return_10y")]:
            target = close.index[-1] - pd.Timedelta(days=365 * years)
            past = close[close.index <= target]
            if past.empty:
                continue  # fund younger than this window
            start = float(past.iloc[-1])
            if start <= 0:
                continue
            total = last / start
            annualized = (total ** (1 / years) - 1) * 100
            out[key] = round(annualized, 2)

        year = close.tail(252)
        if len(year) > 30:
            daily = year.pct_change().dropna()
            out["volatility_1y"] = round(float(daily.std()) * math.sqrt(252) * 100, 2)
    except Exception as e:
        logger.debug(f"ETF returns calc failed: {e}")
    return out


def _holdings(ticker) -> dict:
    """Top holdings and sector weights via yfinance funds_data (best-effort)."""
    out = {"top_holdings": [], "sector_weights": {}}
    try:
        funds = ticker.funds_data
        th = funds.top_holdings
        if th is not None and not th.empty:
            for sym, row in th.iterrows():
                out["top_holdings"].append({
                    "symbol": str(sym),
                    "name": str(row.get("Name", "")),
                    "weight": round(float(row.get("Holding Percent", 0)) * 100, 2),
                })
        sw = funds.sector_weightings
        if sw:
            out["sector_weights"] = {k: round(float(v) * 100, 2) for k, v in sw.items()}
    except Exception as e:
        logger.debug(f"ETF holdings fetch failed: {e}")
    return out


def _num(val) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None
