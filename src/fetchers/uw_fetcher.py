"""Unusual Whales data fetcher — sweeps, blocks, dark pool, institutional activity."""

from datetime import datetime
from typing import Any

from src.fetchers.base import BaseFetcher
from config.settings import get_settings


class UnusualWhalesFetcher(BaseFetcher):
    @property
    def api_name(self) -> str:
        return "unusual_whales"

    @property
    def cache_ttl(self) -> int:
        return 120  # 2 min — flow is time-sensitive

    def __init__(self):
        super().__init__()
        settings = get_settings()
        self._api_key = settings.api_keys.unusual_whales
        self._client = None
        if self._api_key:
            try:
                from unusualwhales import UnusualWhalesClient
                self._client = UnusualWhalesClient(api_key=self._api_key)
            except ImportError:
                self.logger.warning("unusualwhales-python not installed — UW features disabled")
            except Exception as e:
                self.logger.warning(f"Failed to init UW client: {e}")

    @property
    def available(self) -> bool:
        return self._client is not None

    def get_flow_alerts(self, symbol: str, limit: int = 50) -> list[dict]:
        """Get sweep/block/golden sweep alerts for a symbol."""
        if not self.available:
            return []

        def _fetch():
            try:
                alerts = self._client.stock.get_flow(symbol=symbol, limit=limit)
                return self._normalize_flow_alerts(alerts, symbol)
            except Exception as e:
                self.logger.warning(f"UW flow alerts failed for {symbol}: {e}")
                return []

        return self.fetch_with_cache(f"uw_flow_{symbol}", _fetch) or []

    def get_dark_pool_prints(self, symbol: str, limit: int = 20) -> list[dict]:
        """Get dark pool prints for a symbol."""
        if not self.available:
            return []

        def _fetch():
            try:
                prints = self._client.darkpool.get_prints(symbol=symbol, limit=limit)
                return self._normalize_dark_pool(prints, symbol)
            except Exception as e:
                self.logger.warning(f"UW dark pool failed for {symbol}: {e}")
                return []

        return self.fetch_with_cache(f"uw_dp_{symbol}", _fetch, ttl=180) or []

    def get_net_flow_by_expiry(self, symbol: str) -> dict:
        """Get net premium flow grouped by expiry."""
        if not self.available:
            return {}

        def _fetch():
            try:
                flow = self._client.stock.get_options_flow(symbol=symbol)
                return self._normalize_flow_by_expiry(flow)
            except Exception as e:
                self.logger.warning(f"UW flow by expiry failed for {symbol}: {e}")
                return {}

        return self.fetch_with_cache(f"uw_flow_expiry_{symbol}", _fetch) or {}

    def get_institutional_activity(self, symbol: str) -> dict:
        """Get institutional/congress trading activity."""
        if not self.available:
            return {}

        def _fetch():
            try:
                data = self._client.stock.get_institutional(symbol=symbol)
                return self._normalize_institutional(data)
            except Exception as e:
                self.logger.warning(f"UW institutional failed for {symbol}: {e}")
                return {}

        return self.fetch_with_cache(f"uw_inst_{symbol}", _fetch, ttl=600) or {}

    def get_flow_intervals(self, symbol: str, interval: str = "5min") -> list[dict]:
        """Get time-bucketed flow for intraday charts."""
        if not self.available:
            return []

        def _fetch():
            try:
                data = self._client.stock.get_flow_by_interval(
                    symbol=symbol, interval=interval
                )
                return self._normalize_flow_intervals(data)
            except Exception as e:
                self.logger.warning(f"UW flow intervals failed for {symbol}: {e}")
                return []

        return self.fetch_with_cache(f"uw_intervals_{symbol}_{interval}", _fetch) or []

    # ── Normalization helpers ──────────────────────────────────

    def _normalize_flow_alerts(self, raw: Any, symbol: str) -> list[dict]:
        """Normalize UW flow alerts to standard format."""
        if not raw:
            return []
        alerts = []
        items = raw if isinstance(raw, list) else getattr(raw, "data", []) or []
        for item in items:
            item_dict = item if isinstance(item, dict) else vars(item) if hasattr(item, '__dict__') else {}
            premium = self._safe_float(item_dict.get("premium")) or 0
            size = self._safe_int(item_dict.get("size")) or 0
            ask_side = self._safe_float(item_dict.get("ask_side_pct"))

            # Classify alert type
            alert_type = "trade"
            if item_dict.get("is_sweep") or item_dict.get("type") == "sweep":
                alert_type = "sweep"
            if item_dict.get("is_block") or size >= 100:
                alert_type = "block"
            if alert_type == "sweep" and ask_side is not None and ask_side >= 0.7:
                alert_type = "golden_sweep"

            # Determine sentiment
            side = str(item_dict.get("side", "") or item_dict.get("put_call", "")).upper()
            sentiment = "neutral"
            if side in ("CALL", "C"):
                sentiment = "bullish"
            elif side in ("PUT", "P"):
                sentiment = "bearish"

            alerts.append({
                "timestamp": str(item_dict.get("date") or item_dict.get("timestamp") or ""),
                "symbol": symbol,
                "strike": self._safe_float(item_dict.get("strike")),
                "expiry": str(item_dict.get("expiry") or item_dict.get("expiration_date") or ""),
                "type": alert_type,
                "side": side,
                "premium": premium,
                "size": size,
                "ask_side_pct": ask_side,
                "sentiment": sentiment,
            })
        return alerts

    def _normalize_dark_pool(self, raw: Any, symbol: str) -> list[dict]:
        if not raw:
            return []
        prints = []
        items = raw if isinstance(raw, list) else getattr(raw, "data", []) or []
        for item in items:
            d = item if isinstance(item, dict) else vars(item) if hasattr(item, '__dict__') else {}
            price = self._safe_float(d.get("price")) or 0
            size = self._safe_int(d.get("size")) or 0
            prints.append({
                "timestamp": str(d.get("date") or d.get("timestamp") or ""),
                "price": price,
                "size": size,
                "notional": price * size,
                "exchange": d.get("exchange") or d.get("market_center") or "",
            })
        return prints

    def _normalize_flow_by_expiry(self, raw: Any) -> dict:
        if not raw:
            return {}
        data = raw if isinstance(raw, dict) else vars(raw) if hasattr(raw, '__dict__') else {}
        return {
            "by_expiry": data.get("by_expiry", []),
            "total_call_premium": self._safe_float(data.get("total_call_premium")) or 0,
            "total_put_premium": self._safe_float(data.get("total_put_premium")) or 0,
        }

    def _normalize_institutional(self, raw: Any) -> dict:
        if not raw:
            return {}
        data = raw if isinstance(raw, dict) else vars(raw) if hasattr(raw, '__dict__') else {}
        trades = data.get("trades", []) or data.get("data", []) or []
        normalized = []
        for t in trades:
            td = t if isinstance(t, dict) else vars(t) if hasattr(t, '__dict__') else {}
            normalized.append({
                "date": str(td.get("date") or td.get("transaction_date") or ""),
                "name": td.get("name") or td.get("representative") or "",
                "type": td.get("type") or td.get("transaction_type") or "",
                "amount": td.get("amount") or td.get("value") or "",
                "shares": self._safe_int(td.get("shares")),
            })
        return {"trades": normalized}

    def _normalize_flow_intervals(self, raw: Any) -> list[dict]:
        if not raw:
            return []
        items = raw if isinstance(raw, list) else getattr(raw, "data", []) or []
        result = []
        for item in items:
            d = item if isinstance(item, dict) else vars(item) if hasattr(item, '__dict__') else {}
            result.append({
                "timestamp": str(d.get("timestamp") or d.get("time") or ""),
                "call_premium": self._safe_float(d.get("call_premium")) or 0,
                "put_premium": self._safe_float(d.get("put_premium")) or 0,
                "net_premium": self._safe_float(d.get("net_premium")) or 0,
            })
        return result

    @staticmethod
    def _safe_float(val) -> float | None:
        if val is None:
            return None
        try:
            return float(val)
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
