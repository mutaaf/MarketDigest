"""Finnhub fetcher — economic calendar and market news."""

from datetime import timedelta
from typing import Any

import finnhub

from config.settings import get_settings
from src.fetchers.base import BaseFetcher, FetcherError
from src.utils.timezone import now_ct


class FinnhubFetcher(BaseFetcher):
    def __init__(self):
        super().__init__()
        settings = get_settings()
        self._api_key = settings.api_keys.finnhub
        self._client: finnhub.Client | None = None

    @property
    def api_name(self) -> str:
        return "finnhub"

    @property
    def cache_ttl(self) -> int:
        return 600  # 10 min

    @property
    def client(self) -> finnhub.Client:
        if self._client is None:
            if not self._api_key:
                raise FetcherError("FINNHUB_API_KEY not configured")
            self._client = finnhub.Client(api_key=self._api_key)
        return self._client

    def get_economic_calendar(self, days_ahead: int = 1) -> list[dict[str, Any]]:
        """Get economic calendar events."""

        def _fetch():
            today = now_ct().date()
            from_date = today.strftime("%Y-%m-%d")
            to_date = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

            try:
                data = self.client.calendar_economic(
                    _from=from_date,
                    to=to_date,
                )
            except finnhub.FinnhubAPIException as e:
                self.logger.warning(f"Economic calendar not available (may require premium): {e}")
                return []

            events = data.get("economicCalendar", [])

            # Filter for major events (US focus)
            major_events = []
            for event in events:
                if event.get("country", "") == "US" and event.get("impact", "") in ("high", "medium"):
                    major_events.append({
                        "event": event.get("event", ""),
                        "date": event.get("date", ""),
                        "time": event.get("time", ""),
                        "impact": event.get("impact", ""),
                        "actual": event.get("actual"),
                        "estimate": event.get("estimate"),
                        "prev": event.get("prev"),
                        "unit": event.get("unit", ""),
                    })

            return major_events

        return self.fetch_with_cache("finnhub_econ_cal", _fetch) or []

    def get_market_news(self, category: str = "general", count: int = 10) -> list[dict[str, Any]]:
        """Get market news headlines."""

        def _fetch():
            news = self.client.general_news(category, min_id=0)
            return [
                {
                    "headline": item.get("headline", ""),
                    "summary": item.get("summary", ""),
                    "source": item.get("source", ""),
                    "url": item.get("url", ""),
                    "datetime": item.get("datetime", 0),
                    "category": item.get("category", ""),
                }
                for item in news[:count]
            ]

        return self.fetch_with_cache(f"finnhub_news_{category}", _fetch) or []

    def get_next_week_calendar(self) -> list[dict[str, Any]]:
        """Get economic calendar for next week."""

        def _fetch():
            today = now_ct().date()
            # Next Monday
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            next_monday = today + timedelta(days=days_until_monday)
            next_friday = next_monday + timedelta(days=4)

            try:
                data = self.client.calendar_economic(
                    _from=next_monday.strftime("%Y-%m-%d"),
                    to=next_friday.strftime("%Y-%m-%d"),
                )
            except finnhub.FinnhubAPIException as e:
                self.logger.warning(f"Economic calendar not available (may require premium): {e}")
                return []

            events = data.get("economicCalendar", [])

            major_events = []
            for event in events:
                if event.get("country", "") == "US" and event.get("impact", "") in ("high", "medium"):
                    major_events.append({
                        "event": event.get("event", ""),
                        "date": event.get("date", ""),
                        "time": event.get("time", ""),
                        "impact": event.get("impact", ""),
                        "estimate": event.get("estimate"),
                        "prev": event.get("prev"),
                    })

            return major_events

        return self.fetch_with_cache("finnhub_next_week_cal", _fetch, ttl=3600) or []

    def get_week_economic_calendar(self) -> list[dict[str, Any]]:
        """Get economic calendar for the full current week (Mon-Fri)."""

        def _fetch():
            today = now_ct().date()
            # Current Monday
            monday = today - timedelta(days=today.weekday())
            friday = monday + timedelta(days=4)

            try:
                data = self.client.calendar_economic(
                    _from=monday.strftime("%Y-%m-%d"),
                    to=friday.strftime("%Y-%m-%d"),
                )
            except finnhub.FinnhubAPIException as e:
                self.logger.warning(f"Week economic calendar not available: {e}")
                return []

            events = data.get("economicCalendar", [])

            major_events = []
            for event in events:
                if event.get("country", "") == "US" and event.get("impact", "") in ("high", "medium"):
                    major_events.append({
                        "event": event.get("event", ""),
                        "date": event.get("date", ""),
                        "time": event.get("time", ""),
                        "impact": event.get("impact", ""),
                        "actual": event.get("actual"),
                        "estimate": event.get("estimate"),
                        "prev": event.get("prev"),
                        "unit": event.get("unit", ""),
                    })

            return major_events

        return self.fetch_with_cache("finnhub_week_econ_cal", _fetch) or []

    def get_earnings_calendar(self, days_ahead: int = 5) -> list[dict[str, Any]]:
        """Get earnings calendar for upcoming days (US only)."""

        def _fetch():
            today = now_ct().date()
            from_date = today.strftime("%Y-%m-%d")
            to_date = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

            try:
                data = self.client.earnings_calendar(
                    _from=from_date,
                    to=to_date,
                    symbol="",
                    international=False,
                )
            except finnhub.FinnhubAPIException as e:
                self.logger.warning(f"Earnings calendar not available (may require premium): {e}")
                return []

            raw = data.get("earningsCalendar", [])
            results = []
            for item in raw:
                results.append({
                    "symbol": item.get("symbol", ""),
                    "date": item.get("date", ""),
                    "eps_actual": item.get("epsActual"),
                    "eps_estimate": item.get("epsEstimate"),
                    "revenue_actual": item.get("revenueActual"),
                    "revenue_estimate": item.get("revenueEstimate"),
                    "hour": item.get("hour", ""),   # bmo / amc / dmh
                    "year": item.get("year"),
                    "quarter": item.get("quarter"),
                })
            return results

        return self.fetch_with_cache("finnhub_earnings_cal", _fetch, ttl=1800) or []
