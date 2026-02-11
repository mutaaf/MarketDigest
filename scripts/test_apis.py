#!/usr/bin/env python3
"""Verify all API connections are working."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_settings
from src.utils.logging_config import setup_logging

logger = setup_logging("test_apis")


def test_yfinance():
    print("\n--- yfinance ---")
    try:
        from src.fetchers.yfinance_fetcher import YFinanceFetcher
        fetcher = YFinanceFetcher()
        data = fetcher.get_current_price("^GSPC")
        if data:
            print(f"  S&P 500: ${data['price']:,.2f} ({data['change_pct']:+.2f}%)")
            return True
        print("  FAILED: No data returned")
        return False
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_twelvedata():
    print("\n--- Twelve Data ---")
    settings = get_settings()
    if not settings.api_keys.twelvedata:
        print("  SKIPPED: No API key configured")
        return None
    try:
        from src.fetchers.twelvedata_fetcher import TwelveDataFetcher
        fetcher = TwelveDataFetcher()
        data = fetcher.get_forex_quote("EUR/USD")
        if data:
            print(f"  EUR/USD: {data['price']:.5f} ({data['change_pct']:+.2f}%)")
            return True
        print("  FAILED: No data returned")
        return False
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_finnhub():
    print("\n--- Finnhub ---")
    settings = get_settings()
    if not settings.api_keys.finnhub:
        print("  SKIPPED: No API key configured")
        return None
    try:
        from src.fetchers.finnhub_fetcher import FinnhubFetcher
        fetcher = FinnhubFetcher()
        events = fetcher.get_economic_calendar()
        print(f"  Economic calendar: {len(events)} upcoming US events")
        news = fetcher.get_market_news(count=3)
        print(f"  Market news: {len(news)} headlines")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_fred():
    print("\n--- FRED ---")
    settings = get_settings()
    if not settings.api_keys.fred:
        print("  SKIPPED: No API key configured")
        return None
    try:
        from src.fetchers.fred_fetcher import FREDFetcher
        fetcher = FREDFetcher()
        data = fetcher.get_series_latest("DGS10")
        if data:
            print(f"  10Y Treasury: {data['value']:.2f}% (as of {data['date']})")
            return True
        print("  FAILED: No data returned")
        return False
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_newsapi():
    print("\n--- NewsAPI ---")
    settings = get_settings()
    if not settings.api_keys.newsapi:
        print("  SKIPPED: No API key configured")
        return None
    try:
        from src.fetchers.newsapi_fetcher import NewsAPIFetcher
        fetcher = NewsAPIFetcher()
        headlines = fetcher.get_top_business_headlines(count=3)
        print(f"  Business headlines: {len(headlines)} articles")
        if headlines:
            print(f"  Latest: {headlines[0]['title'][:60]}...")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_feargreed():
    print("\n--- Fear & Greed Index ---")
    try:
        from src.fetchers.feargreed_fetcher import FearGreedFetcher
        fetcher = FearGreedFetcher()
        data = fetcher.get_fear_greed_index()
        if data:
            print(f"  Score: {data['score']} — {data['classification']}")
            return True
        print("  FAILED: No data returned")
        return False
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def main():
    print("=" * 50)
    print("Financial Market Digest — API Connection Test")
    print("=" * 50)

    results = {
        "yfinance": test_yfinance(),
        "Twelve Data": test_twelvedata(),
        "Finnhub": test_finnhub(),
        "FRED": test_fred(),
        "NewsAPI": test_newsapi(),
        "Fear & Greed": test_feargreed(),
    }

    print("\n" + "=" * 50)
    print("RESULTS SUMMARY")
    print("=" * 50)
    for api, result in results.items():
        if result is True:
            status = "PASS"
        elif result is None:
            status = "SKIP (no key)"
        else:
            status = "FAIL"
        print(f"  {api:15s} {status}")

    failed = [k for k, v in results.items() if v is False]
    if failed:
        print(f"\nFailed APIs: {', '.join(failed)}")
        print("Check your .env file and API keys.")
        sys.exit(1)
    else:
        print("\nAll configured APIs are working!")


if __name__ == "__main__":
    main()
