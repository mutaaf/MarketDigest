"""Alpha Vantage options data fetcher — historical chains, Greeks, historical IV."""

import math
from datetime import datetime
from typing import Any

import requests

from src.fetchers.base import BaseFetcher
from config.settings import get_settings


class AlphaVantageOptionsFetcher(BaseFetcher):
    BASE_URL = "https://www.alphavantage.co/query"

    @property
    def api_name(self) -> str:
        return "alpha_vantage_options"

    @property
    def cache_ttl(self) -> int:
        return 3600  # 1 hour — historical data

    def __init__(self):
        super().__init__()
        settings = get_settings()
        self._api_key = settings.api_keys.alpha_vantage

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def _request(self, params: dict) -> dict | None:
        params["apikey"] = self._api_key
        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if "Error Message" in data or "Note" in data:
                self.logger.warning(f"AV API error: {data.get('Error Message') or data.get('Note')}")
                return None
            return data
        except Exception as e:
            self.logger.warning(f"AV request failed: {e}")
            return None

    def get_historical_chain(self, symbol: str, date: str | None = None) -> dict | None:
        """Fetch options chain (current or historical date)."""
        if not self.available:
            return None

        def _fetch():
            params = {"function": "HISTORICAL_OPTIONS", "symbol": symbol}
            if date:
                params["date"] = date
            data = self._request(params)
            if not data or "data" not in data:
                return None
            return self._normalize_chain(data, symbol)

        cache_key = f"av_chain_{symbol}_{date or 'current'}"
        return self.fetch_with_cache(cache_key, _fetch)

    def get_historical_iv(self, symbol: str, days: int = 90) -> list[dict]:
        """Fetch historical implied volatility data points."""
        if not self.available:
            return []

        def _fetch():
            # Use the realtime options endpoint and extract IV data
            params = {"function": "HISTORICAL_OPTIONS", "symbol": symbol}
            data = self._request(params)
            if not data or "data" not in data:
                return []
            return self._extract_iv_history(data["data"])

        return self.fetch_with_cache(f"av_hist_iv_{symbol}", _fetch) or []

    def get_greeks(self, symbol: str, expiry: str, strike: float, option_type: str) -> dict | None:
        """Get pre-calculated Greeks for a specific contract."""
        if not self.available:
            return None

        def _fetch():
            params = {
                "function": "HISTORICAL_OPTIONS",
                "symbol": symbol,
                "date": expiry,
            }
            data = self._request(params)
            if not data or "data" not in data:
                return None
            # Find matching contract
            for contract in data["data"]:
                c_strike = self._safe_float(contract.get("strike"))
                c_type = contract.get("type", "").lower()
                if c_strike == strike and c_type == option_type.lower():
                    return {
                        "delta": self._safe_float(contract.get("delta")),
                        "gamma": self._safe_float(contract.get("gamma")),
                        "theta": self._safe_float(contract.get("theta")),
                        "vega": self._safe_float(contract.get("vega")),
                        "rho": self._safe_float(contract.get("rho")),
                        "iv": self._safe_float(contract.get("implied_volatility")),
                    }
            return None

        return self.fetch_with_cache(
            f"av_greeks_{symbol}_{expiry}_{strike}_{option_type}", _fetch
        )

    def _normalize_chain(self, raw: dict, symbol: str) -> dict:
        """Normalize AV chain data to match yfinance format."""
        chains: dict[str, dict] = {}
        for contract in raw.get("data", []):
            expiry = contract.get("expiration")
            if not expiry:
                continue
            if expiry not in chains:
                chains[expiry] = {"calls": [], "puts": []}

            option_type = (contract.get("type") or "").lower()
            entry = {
                "strike": self._safe_float(contract.get("strike")),
                "bid": self._safe_float(contract.get("bid")) or 0.0,
                "ask": self._safe_float(contract.get("ask")) or 0.0,
                "volume": self._safe_int(contract.get("volume")),
                "openInterest": self._safe_int(contract.get("open_interest")),
                "impliedVolatility": self._safe_float(contract.get("implied_volatility")),
                "inTheMoney": contract.get("in_the_money", "FALSE").upper() == "TRUE",
                "delta": self._safe_float(contract.get("delta")),
                "gamma": self._safe_float(contract.get("gamma")),
                "theta": self._safe_float(contract.get("theta")),
                "vega": self._safe_float(contract.get("vega")),
                "rho": self._safe_float(contract.get("rho")),
            }
            if option_type == "call":
                chains[expiry]["calls"].append(entry)
            elif option_type == "put":
                chains[expiry]["puts"].append(entry)

        return {
            "symbol": symbol,
            "stock_price": None,  # AV doesn't include stock price
            "expirations": sorted(chains.keys()),
            "chains": chains,
            "fetched_at": datetime.now().isoformat(),
            "provider": "alpha_vantage",
        }

    def _extract_iv_history(self, data: list) -> list[dict]:
        """Extract IV data points from historical options data."""
        iv_points: dict[str, list[float]] = {}
        for contract in data:
            date = contract.get("date") or contract.get("expiration")
            iv = self._safe_float(contract.get("implied_volatility"))
            if date and iv is not None and iv > 0:
                if date not in iv_points:
                    iv_points[date] = []
                iv_points[date].append(iv)

        result = []
        for date, ivs in sorted(iv_points.items()):
            avg_iv = sum(ivs) / len(ivs) if ivs else 0
            result.append({
                "date": date,
                "avg_iv": round(avg_iv, 4),
                "min_iv": round(min(ivs), 4) if ivs else 0,
                "max_iv": round(max(ivs), 4) if ivs else 0,
            })
        return result

    @staticmethod
    def _safe_float(val) -> float | None:
        if val is None:
            return None
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return None
            return round(f, 6)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(val) -> int:
        if val is None:
            return 0
        try:
            return int(float(val))
        except (TypeError, ValueError):
            return 0
