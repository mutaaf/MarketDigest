"""FRED fetcher — CPI, GDP, employment, rates."""

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from fredapi import Fred

from config.settings import get_settings
from src.fetchers.base import BaseFetcher, FetcherError
from src.utils.timezone import now_ct


class FREDFetcher(BaseFetcher):
    def __init__(self):
        super().__init__()
        settings = get_settings()
        self._api_key = settings.api_keys.fred
        self._client: Fred | None = None

    @property
    def api_name(self) -> str:
        return "fred"

    @property
    def cache_ttl(self) -> int:
        return 3600  # 1 hour — economic data doesn't change fast

    @property
    def client(self) -> Fred:
        if self._client is None:
            if not self._api_key:
                raise FetcherError("FRED_API_KEY not configured")
            self._client = Fred(api_key=self._api_key)
        return self._client

    def get_series_latest(self, series_id: str) -> dict[str, Any] | None:
        """Get latest value for a FRED series."""

        def _fetch():
            data = self.client.get_series(series_id, observation_start=(datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"))
            if data is None or data.empty:
                return None

            latest = data.dropna().iloc[-1]
            prev = data.dropna().iloc[-2] if len(data.dropna()) > 1 else latest

            return {
                "series_id": series_id,
                "value": round(float(latest), 4),
                "prev_value": round(float(prev), 4),
                "date": str(data.dropna().index[-1].date()),
                "change": round(float(latest - prev), 4),
            }

        return self.fetch_with_cache(f"fred_{series_id}", _fetch)

    def get_all_economic_data(self) -> dict[str, dict[str, Any]]:
        """Get latest values for all configured FRED series."""
        settings = get_settings()
        series_list = settings.instruments.get("economic", {}).get("fred_series", [])

        results = {}
        for series_info in series_list:
            series_id = series_info["series_id"]
            try:
                data = self.get_series_latest(series_id)
                if data:
                    data["name"] = series_info["name"]
                    data["frequency"] = series_info["frequency"]
                    results[series_id] = data
            except Exception as e:
                self.logger.warning(f"Failed to fetch FRED {series_id}: {e}")
                continue

        return results

    def get_yield_spread(self) -> dict[str, Any] | None:
        """Get 10Y-2Y yield spread (recession indicator)."""

        def _fetch():
            ten_y = self.get_series_latest("DGS10")
            two_y = self.get_series_latest("DGS2")
            if ten_y and two_y:
                spread = ten_y["value"] - two_y["value"]
                return {
                    "ten_year": ten_y["value"],
                    "two_year": two_y["value"],
                    "spread": round(spread, 4),
                    "inverted": spread < 0,
                }
            return None

        return self.fetch_with_cache("fred_yield_spread", _fetch)
