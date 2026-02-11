"""Twelve Data fetcher — real-time forex and intraday indicators."""

from typing import Any

from twelvedata import TDClient

from config.settings import get_settings
from src.fetchers.base import BaseFetcher, FetcherError


class TwelveDataFetcher(BaseFetcher):
    def __init__(self):
        super().__init__()
        settings = get_settings()
        self._api_key = settings.api_keys.twelvedata
        self._client: TDClient | None = None

    @property
    def api_name(self) -> str:
        return "twelvedata"

    @property
    def cache_ttl(self) -> int:
        return 180  # 3 min — conserve API calls

    @property
    def client(self) -> TDClient:
        if self._client is None:
            if not self._api_key:
                raise FetcherError("TWELVEDATA_API_KEY not configured")
            self._client = TDClient(apikey=self._api_key)
        return self._client

    def get_forex_quote(self, symbol: str) -> dict[str, Any] | None:
        """Get real-time forex quote. symbol format: 'EUR/USD'."""

        def _fetch():
            data = self.client.quote(symbol=symbol).as_json()
            if not data or "close" not in data:
                return None
            return {
                "symbol": symbol,
                "price": float(data.get("close", 0)),
                "open": float(data.get("open", 0)),
                "high": float(data.get("high", 0)),
                "low": float(data.get("low", 0)),
                "prev_close": float(data.get("previous_close", 0)),
                "change": float(data.get("change", 0)),
                "change_pct": float(data.get("percent_change", 0)),
                "volume": int(data.get("volume", 0)),
            }

        return self.fetch_with_cache(f"td_quote_{symbol}", _fetch)

    def get_forex_timeseries(self, symbol: str, interval: str = "1h", outputsize: int = 24) -> list[dict] | None:
        """Get intraday forex time series."""

        def _fetch():
            data = self.client.time_series(
                symbol=symbol,
                interval=interval,
                outputsize=outputsize,
            ).as_json()
            if not data:
                return None
            return [
                {
                    "datetime": bar.get("datetime", ""),
                    "open": float(bar.get("open", 0)),
                    "high": float(bar.get("high", 0)),
                    "low": float(bar.get("low", 0)),
                    "close": float(bar.get("close", 0)),
                    "volume": int(bar.get("volume", 0)),
                }
                for bar in data
            ]

        return self.fetch_with_cache(f"td_ts_{symbol}_{interval}", _fetch)

    def get_rsi(self, symbol: str, interval: str = "1day", period: int = 14) -> float | None:
        """Get RSI for a forex pair."""

        def _fetch():
            data = self.client.rsi(
                symbol=symbol,
                interval=interval,
                time_period=period,
                outputsize=1,
            ).as_json()
            if data and len(data) > 0:
                return float(data[0].get("rsi", 0))
            return None

        return self.fetch_with_cache(f"td_rsi_{symbol}_{interval}", _fetch, ttl=300)

    def get_pivot_points(self, symbol: str) -> dict[str, float] | None:
        """Calculate pivot points from daily data."""

        def _fetch():
            data = self.client.time_series(
                symbol=symbol,
                interval="1day",
                outputsize=2,
            ).as_json()
            if not data or len(data) < 1:
                return None

            prev = data[0]  # Most recent completed day
            h = float(prev["high"])
            l = float(prev["low"])
            c = float(prev["close"])

            pivot = (h + l + c) / 3
            r1 = 2 * pivot - l
            s1 = 2 * pivot - h
            r2 = pivot + (h - l)
            s2 = pivot - (h - l)

            return {
                "pivot": round(pivot, 5),
                "r1": round(r1, 5),
                "r2": round(r2, 5),
                "s1": round(s1, 5),
                "s2": round(s2, 5),
            }

        return self.fetch_with_cache(f"td_pivot_{symbol}", _fetch, ttl=3600)
