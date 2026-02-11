"""yfinance fetcher — the workhorse. Stocks, indices, commodities, daily forex."""

import math
from typing import Any

import pandas as pd
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


class YFinanceFetcher(BaseFetcher):
    @property
    def api_name(self) -> str:
        return "yfinance"

    @property
    def cache_ttl(self) -> int:
        return 120  # 2 min — yfinance is free

    def get_current_price(self, ticker: str) -> dict[str, Any] | None:
        """Get current/latest price data for a single ticker."""

        def _fetch():
            t = yf.Ticker(ticker)
            info = t.fast_info
            hist = t.history(period="2d")
            if hist.empty:
                return None

            latest = hist.iloc[-1]
            price = _clean_float(latest["Close"])
            if price is None:
                return None

            prev_close = _clean_float(
                hist.iloc[-2]["Close"] if len(hist) > 1 else latest["Close"]
            ) or price
            change = price - prev_close
            change_pct = (change / prev_close) * 100 if prev_close else 0

            return {
                "ticker": ticker,
                "price": price,
                "open": _clean_float(latest["Open"]) or price,
                "high": _clean_float(latest["High"]) or price,
                "low": _clean_float(latest["Low"]) or price,
                "close": price,
                "volume": int(latest.get("Volume", 0)),
                "prev_close": prev_close,
                "change": _clean_float(change) or 0.0,
                "change_pct": _clean_float(change_pct, decimals=2) or 0.0,
            }

        return self.fetch_with_cache(f"yf_price_{ticker}", _fetch)

    def get_batch_prices(self, tickers: list[str]) -> dict[str, dict[str, Any]]:
        """Get prices for multiple tickers at once."""

        def _fetch():
            data = yf.download(tickers, period="2d", group_by="ticker", progress=False, threads=True)
            results = {}

            for ticker in tickers:
                try:
                    if len(tickers) == 1:
                        df = data
                    else:
                        df = data[ticker] if ticker in data.columns.get_level_values(0) else pd.DataFrame()

                    if df.empty or len(df) < 1:
                        continue

                    latest = df.iloc[-1]
                    price = _clean_float(latest["Close"])
                    if price is None:
                        continue

                    prev_close = _clean_float(
                        df.iloc[-2]["Close"] if len(df) > 1 else latest["Close"]
                    ) or price
                    change = price - prev_close
                    change_pct = (change / prev_close) * 100 if prev_close else 0

                    results[ticker] = {
                        "ticker": ticker,
                        "price": price,
                        "open": _clean_float(latest["Open"]) or price,
                        "high": _clean_float(latest["High"]) or price,
                        "low": _clean_float(latest["Low"]) or price,
                        "close": price,
                        "volume": int(latest.get("Volume", 0)),
                        "prev_close": prev_close,
                        "change": _clean_float(change) or 0.0,
                        "change_pct": _clean_float(change_pct, decimals=2) or 0.0,
                    }
                except Exception as e:
                    self.logger.warning(f"Failed to parse {ticker}: {e}")
                    continue

            return results

        cache_key = f"yf_batch_{'_'.join(sorted(tickers[:5]))}_{len(tickers)}"
        return self.fetch_with_cache(cache_key, _fetch) or {}

    def get_history(self, ticker: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame | None:
        """Get historical OHLCV data."""

        def _fetch():
            t = yf.Ticker(ticker)
            hist = t.history(period=period, interval=interval)
            if hist.empty:
                return None
            return hist

        cache_key = f"yf_hist_{ticker}_{period}_{interval}"
        return self.fetch_with_cache(cache_key, _fetch, ttl=600)

    def get_intraday(self, ticker: str, period: str = "1d", interval: str = "5m") -> pd.DataFrame | None:
        """Get intraday data."""

        def _fetch():
            t = yf.Ticker(ticker)
            hist = t.history(period=period, interval=interval)
            if hist.empty:
                return None
            return hist

        cache_key = f"yf_intraday_{ticker}_{period}_{interval}"
        return self.fetch_with_cache(cache_key, _fetch, ttl=120)

    def get_weekly_data(self, ticker: str) -> pd.DataFrame | None:
        """Get weekly OHLCV for weekly digest."""

        def _fetch():
            t = yf.Ticker(ticker)
            hist = t.history(period="3mo", interval="1wk")
            if hist.empty:
                return None
            return hist

        return self.fetch_with_cache(f"yf_weekly_{ticker}", _fetch, ttl=3600)
