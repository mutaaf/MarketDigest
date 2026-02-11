"""Orchestrator: fetch -> analyze -> assemble digest (with fallbacks)."""

from typing import Any

import pandas as pd

from config.settings import get_settings, get_all_yfinance_tickers
from src.fetchers.yfinance_fetcher import YFinanceFetcher
from src.fetchers.twelvedata_fetcher import TwelveDataFetcher
from src.fetchers.finnhub_fetcher import FinnhubFetcher
from src.fetchers.fred_fetcher import FREDFetcher
from src.fetchers.newsapi_fetcher import NewsAPIFetcher
from src.fetchers.feargreed_fetcher import FearGreedFetcher
from src.fetchers.base import FetcherError
from src.analysis.technicals import full_analysis
from src.analysis.sentiment import compute_composite_sentiment
from src.analysis.performance import get_top_movers, sector_comparison
from src.analysis.session_tracker import get_overnight_recap, get_session_levels
from src.cache.manager import cache
from src.utils.logging_config import get_logger

logger = get_logger("builder")


class DigestBuilder:
    """Fetches all data with fallbacks, runs analysis, and provides to templates."""

    def __init__(self):
        self.settings = get_settings()
        self.yf = YFinanceFetcher()
        self.td = TwelveDataFetcher() if self.settings.has_api_key("twelvedata") else None
        self.finnhub = FinnhubFetcher() if self.settings.has_api_key("finnhub") else None
        self.fred = FREDFetcher() if self.settings.has_api_key("fred") else None
        self.newsapi = NewsAPIFetcher() if self.settings.has_api_key("newsapi") else None
        self.fg = FearGreedFetcher()

    # ── Price Data ──────────────────────────────────────────────

    def fetch_all_prices(self) -> dict[str, dict[str, Any]]:
        """Fetch prices for all instruments. yfinance is primary."""
        all_tickers = get_all_yfinance_tickers()
        yf_symbols = [t["yfinance"] for t in all_tickers if t.get("yfinance")]

        prices = {}
        try:
            batch = self.yf.get_batch_prices(yf_symbols)
            # Map yfinance ticker back to our symbol
            yf_to_info = {t["yfinance"]: t for t in all_tickers}
            for yf_sym, data in batch.items():
                info = yf_to_info.get(yf_sym, {})
                key = info.get("symbol", yf_sym)
                prices[key] = {
                    **data,
                    "name": info.get("name", yf_sym),
                    "category": info.get("category", "other"),
                }
        except Exception as e:
            logger.error(f"Batch price fetch failed: {e}")
            # Fallback: fetch individually
            for t in all_tickers:
                try:
                    data = self.yf.get_current_price(t["yfinance"])
                    if data:
                        prices[t["symbol"]] = {
                            **data,
                            "name": t.get("name", t["symbol"]),
                            "category": t.get("category", "other"),
                        }
                except Exception:
                    continue

        return prices

    def fetch_forex_prices(self) -> dict[str, dict[str, Any]]:
        """Fetch forex prices. Try TwelveData for real-time, fall back to yfinance."""
        instruments = self.settings.instruments
        pairs = instruments.get("forex", {}).get("majors", [])
        results = {}

        for pair in pairs:
            data = None
            # Try TwelveData first for real-time
            if self.td and pair.get("twelvedata"):
                try:
                    data = self.td.get_forex_quote(pair["twelvedata"])
                    if data:
                        data["name"] = pair["name"]
                        data["category"] = "forex"
                except Exception:
                    pass

            # Fallback to yfinance
            if data is None and pair.get("yfinance"):
                try:
                    data = self.yf.get_current_price(pair["yfinance"])
                    if data:
                        data["name"] = pair["name"]
                        data["category"] = "forex"
                except Exception:
                    pass

            if data:
                results[pair["symbol"]] = data

        # DXY
        dxy_info = instruments.get("forex", {}).get("indices", [{}])[0]
        if dxy_info.get("yfinance"):
            try:
                dxy = self.yf.get_current_price(dxy_info["yfinance"])
                if dxy:
                    dxy["name"] = dxy_info.get("name", "DXY")
                    dxy["category"] = "forex_index"
                    results["DXY"] = dxy
            except Exception:
                pass

        return results

    def fetch_forex_pivots(self) -> dict[str, dict[str, float]]:
        """Fetch pivot points for forex pairs."""
        if not self.td:
            return {}

        instruments = self.settings.instruments
        pairs = instruments.get("forex", {}).get("majors", [])
        results = {}

        for pair in pairs:
            td_sym = pair.get("twelvedata")
            if td_sym:
                try:
                    pivots = self.td.get_pivot_points(td_sym)
                    if pivots:
                        results[pair["symbol"]] = pivots
                except Exception:
                    continue

        return results

    def fetch_futures_prices(self) -> dict[str, dict[str, Any]]:
        """Fetch US futures prices."""
        instruments = self.settings.instruments
        futures = instruments.get("us_indices", {}).get("futures", [])
        results = {}

        for fut in futures:
            try:
                data = self.yf.get_current_price(fut["yfinance"])
                if data:
                    data["name"] = fut["name"]
                    data["category"] = "us_futures"
                    results[fut["symbol"]] = data
            except Exception:
                continue

        return results

    def fetch_commodity_prices(self) -> dict[str, dict[str, Any]]:
        """Fetch commodity prices by subcategory."""
        instruments = self.settings.instruments
        results = {}

        for sub in ["metals", "energy", "agriculture"]:
            items = instruments.get("commodities", {}).get(sub, [])
            for item in items:
                try:
                    data = self.yf.get_current_price(item["yfinance"])
                    if data:
                        data["name"] = item["name"]
                        data["category"] = sub
                        results[item["symbol"]] = data
                except Exception:
                    continue

        return results

    def fetch_crypto_prices(self) -> dict[str, dict[str, Any]]:
        """Fetch cryptocurrency prices."""
        instruments = self.settings.instruments
        results = {}

        for item in instruments.get("crypto", []):
            try:
                data = self.yf.get_current_price(item["yfinance"])
                if data:
                    data["name"] = item["name"]
                    data["category"] = "crypto"
                    results[item["symbol"]] = data
            except Exception:
                continue

        return results

    def fetch_daytrade_universe(self) -> dict[str, dict[str, Any]]:
        """Fetch prices for all day-trade-eligible instruments (existing + us_stocks)."""
        instruments = self.settings.instruments

        # Collect us_stocks tickers
        us_stocks = instruments.get("us_stocks", [])
        stock_tickers = [s for s in us_stocks if s.get("enabled", True) and s.get("yfinance")]

        # Also include existing tradable instruments (indices, commodities, crypto)
        all_tickers = get_all_yfinance_tickers()
        non_stock_tickers = [t for t in all_tickers if t.get("category") != "us_stock"]

        combined = non_stock_tickers + stock_tickers
        yf_symbols = [t["yfinance"] for t in combined if t.get("yfinance")]

        prices = {}
        try:
            batch = self.yf.get_batch_prices(yf_symbols)
            yf_to_info = {t["yfinance"]: t for t in combined}
            for yf_sym, data in batch.items():
                info = yf_to_info.get(yf_sym, {})
                key = info.get("symbol", yf_sym)
                prices[key] = {
                    **data,
                    "name": info.get("name", yf_sym),
                    "category": info.get("category", "other"),
                }
        except Exception as e:
            logger.error(f"Daytrade universe batch fetch failed: {e}")

        return prices

    # ── Analysis ────────────────────────────────────────────────

    def run_technicals(self, tickers: list[dict] | None = None) -> dict[str, dict]:
        """Run technical analysis on all instruments."""
        if tickers is None:
            tickers = get_all_yfinance_tickers()

        results = {}
        for t in tickers:
            yf_sym = t.get("yfinance")
            if not yf_sym:
                continue
            try:
                hist = self.yf.get_history(yf_sym, period="3mo", interval="1d")
                if hist is not None and not hist.empty:
                    analysis = full_analysis(hist, ticker=t.get("symbol", yf_sym))
                    analysis["name"] = t.get("name", yf_sym)
                    analysis["category"] = t.get("category", "other")
                    results[t["symbol"]] = analysis
            except Exception as e:
                logger.debug(f"Technical analysis failed for {yf_sym}: {e}")
                continue

        return results

    def compute_sentiment(self, prices: dict | None = None, technicals: dict | None = None) -> dict[str, Any]:
        """Compute composite sentiment score."""
        # VIX
        vix_value = None
        if prices and "VIX" in prices:
            vix_value = prices["VIX"].get("price")

        # DXY change
        dxy_change = None
        if prices and "DXY" in prices:
            dxy_change = prices["DXY"].get("change_pct")

        # Fear & Greed
        fg_data = None
        try:
            fg_data = self.fg.get_fear_greed_index()
        except Exception:
            pass

        # News
        headlines = []
        if self.newsapi:
            try:
                headlines = self.newsapi.get_market_headlines(count=15)
            except Exception:
                pass
        if not headlines and self.finnhub:
            try:
                news = self.finnhub.get_market_news(count=15)
                headlines = [{"title": n["headline"], "description": n.get("summary", "")} for n in news]
            except Exception:
                pass

        # Technical breadth
        tech_list = list(technicals.values()) if technicals else []

        return compute_composite_sentiment(
            vix_value=vix_value,
            dxy_change_pct=dxy_change,
            fg_data=fg_data,
            headlines=headlines,
            tech_analyses=tech_list,
        )

    # ── Economic Data ───────────────────────────────────────────

    def fetch_economic_calendar(self, days_ahead: int = 1) -> list[dict]:
        if self.finnhub:
            try:
                return self.finnhub.get_economic_calendar(days_ahead)
            except Exception as e:
                logger.warning(f"Economic calendar fetch failed: {e}")
        return []

    def fetch_next_week_calendar(self) -> list[dict]:
        if self.finnhub:
            try:
                return self.finnhub.get_next_week_calendar()
            except Exception as e:
                logger.warning(f"Next week calendar fetch failed: {e}")
        return []

    def fetch_week_economic_calendar(self) -> list[dict]:
        """Fetch full current week economic calendar."""
        if self.finnhub:
            try:
                return self.finnhub.get_week_economic_calendar()
            except Exception as e:
                logger.warning(f"Week economic calendar fetch failed: {e}")
        return []

    def fetch_earnings_calendar(self, days_ahead: int = 5) -> list[dict]:
        """Fetch earnings calendar for upcoming days."""
        if self.finnhub:
            try:
                return self.finnhub.get_earnings_calendar(days_ahead)
            except Exception as e:
                logger.warning(f"Earnings calendar fetch failed: {e}")
        return []

    def fetch_comprehensive_events(self, scope: str = "today") -> dict:
        """Fetch and classify all events (economic + earnings + forward calendar).

        Args:
            scope: "today", "tomorrow", "week", or "next_week"

        Returns dict with:
            economic_events, earnings_bellwether, earnings_other,
            earnings_other_count, earnings_total, forward_calendar
        """
        from src.analysis.events import classify_earnings, get_forward_calendar

        # Economic events
        if scope == "today":
            econ_events = self.fetch_economic_calendar(days_ahead=0)
        elif scope == "tomorrow":
            econ_events = self.fetch_economic_calendar(days_ahead=1)
        elif scope == "week":
            econ_events = self.fetch_week_economic_calendar()
        elif scope == "next_week":
            econ_events = self.fetch_next_week_calendar()
        else:
            econ_events = self.fetch_economic_calendar(days_ahead=0)

        # Earnings
        days = 5 if scope in ("week", "next_week") else 1
        raw_earnings = self.fetch_earnings_calendar(days_ahead=days)
        bellwether, other, total = classify_earnings(raw_earnings)

        # Forward calendar
        forward = get_forward_calendar()

        return {
            "economic_events": econ_events,
            "earnings_bellwether": bellwether,
            "earnings_other": other,
            "earnings_other_count": len(other),
            "earnings_total": total,
            "forward_calendar": forward,
        }

    def fetch_economic_data(self) -> dict[str, dict]:
        if self.fred:
            try:
                return self.fred.get_all_economic_data()
            except Exception as e:
                logger.warning(f"FRED data fetch failed: {e}")
        return {}

    def fetch_yield_spread(self) -> dict | None:
        if self.fred:
            try:
                return self.fred.get_yield_spread()
            except Exception:
                pass
        return None

    # ── Session Data ────────────────────────────────────────────

    def fetch_overnight_data(self) -> dict[str, Any]:
        """Get overnight session data for morning digest."""
        instruments = self.settings.instruments
        forex_pairs = instruments.get("forex", {}).get("majors", [])

        intraday_data = {}
        name_map = {}

        for pair in forex_pairs[:4]:  # Limit to conserve API calls
            yf_sym = pair.get("yfinance")
            if yf_sym:
                try:
                    df = self.yf.get_intraday(yf_sym, period="2d", interval="1h")
                    if df is not None:
                        intraday_data[pair["symbol"]] = df
                        name_map[pair["symbol"]] = pair["name"]
                except Exception:
                    continue

        if intraday_data:
            return get_overnight_recap(intraday_data, name_map)
        return {"sydney": {}, "tokyo": {}}

    # ── Snapshot Persistence ────────────────────────────────────

    def save_morning_snapshot(self, sentiment: dict, prices: dict) -> None:
        """Save morning state for afternoon comparison."""
        cache.set("morning_snapshot", {
            "sentiment": sentiment,
            "prices": {k: {"price": v.get("price"), "change_pct": v.get("change_pct")}
                       for k, v in prices.items()},
        }, persist=True)

    def get_morning_snapshot(self) -> dict | None:
        """Retrieve morning snapshot for comparison."""
        return cache.get_stale("morning_snapshot")

    # ── LLM Provider ─────────────────────────────────────────────

    def get_llm_provider(self):
        """Return an LLMProvider instance if any LLM keys are configured, else None."""
        if not self.settings.has_llm_key():
            return None
        from src.analysis.llm_providers import LLMProvider
        return LLMProvider()
