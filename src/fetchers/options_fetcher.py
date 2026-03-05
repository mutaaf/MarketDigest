"""Options chain data fetcher via yfinance."""

import math
from datetime import datetime
from typing import Any

import yfinance as yf

from src.fetchers.base import BaseFetcher


def _clean_float(value, decimals: int = 4) -> float | None:
    """Convert to float, returning None for NaN/Inf."""
    if value is None:
        return None
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, decimals)
    except (TypeError, ValueError):
        return None


def _safe_int(value) -> int:
    """Convert to int, returning 0 for NaN/None."""
    if value is None:
        return 0
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return 0
        return int(f)
    except (TypeError, ValueError):
        return 0


class OptionsFetcher(BaseFetcher):
    @property
    def api_name(self) -> str:
        return "yfinance_options"

    @property
    def cache_ttl(self) -> int:
        return 300  # 5 min

    def get_expirations(self, symbol: str) -> list[str] | None:
        """Get available option expiration dates for a symbol."""
        def _fetch():
            t = yf.Ticker(symbol)
            try:
                exps = t.options
            except Exception:
                return None
            if not exps:
                return None
            return list(exps)

        return self.fetch_with_cache(f"opts_exp_{symbol}", _fetch)

    def get_option_chain(self, symbol: str, max_expirations: int = 6) -> dict[str, Any] | None:
        """Fetch option chains for up to max_expirations nearest dates."""
        def _fetch():
            t = yf.Ticker(symbol)
            try:
                exps = t.options
            except Exception:
                return None
            if not exps:
                return None

            # Get stock price
            hist = t.history(period="1d")
            if hist.empty:
                return None
            stock_price = _clean_float(hist["Close"].iloc[-1])
            if stock_price is None:
                return None

            exps_to_fetch = list(exps[:max_expirations])
            chains: dict[str, dict] = {}

            for exp in exps_to_fetch:
                try:
                    chain = t.option_chain(exp)
                except Exception:
                    continue

                calls = []
                for _, row in chain.calls.iterrows():
                    calls.append({
                        "strike": _clean_float(row.get("strike")),
                        "bid": _clean_float(row.get("bid")) or 0.0,
                        "ask": _clean_float(row.get("ask")) or 0.0,
                        "volume": _safe_int(row.get("volume")),
                        "openInterest": _safe_int(row.get("openInterest")),
                        "impliedVolatility": _clean_float(row.get("impliedVolatility")),
                        "inTheMoney": bool(row.get("inTheMoney", False)),
                    })

                puts = []
                for _, row in chain.puts.iterrows():
                    puts.append({
                        "strike": _clean_float(row.get("strike")),
                        "bid": _clean_float(row.get("bid")) or 0.0,
                        "ask": _clean_float(row.get("ask")) or 0.0,
                        "volume": _safe_int(row.get("volume")),
                        "openInterest": _safe_int(row.get("openInterest")),
                        "impliedVolatility": _clean_float(row.get("impliedVolatility")),
                        "inTheMoney": bool(row.get("inTheMoney", False)),
                    })

                chains[exp] = {"calls": calls, "puts": puts}

            if not chains:
                return None

            return {
                "symbol": symbol,
                "stock_price": stock_price,
                "expirations": exps_to_fetch,
                "chains": chains,
                "fetched_at": datetime.now().isoformat(),
            }

        return self.fetch_with_cache(f"opts_chain_{symbol}", _fetch)
