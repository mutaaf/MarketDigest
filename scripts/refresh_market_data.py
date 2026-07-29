#!/usr/bin/env python3
"""Pull the latest for all market data.

Clears cached market data (prices, ETF profiles, fundamentals — NOT LLM
responses or configs) and immediately re-warms everything the family's
portfolios and watchlists actually use, so screens are instantly fresh.

Run: .venv/bin/python scripts/refresh_market_data.py
Note: also restart the UI server afterwards to drop its in-memory cache:
      launchctl kickstart -k gui/$UID/com.marketdigest.ui
(this script prints the command).
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CACHE_DIR = PROJECT_ROOT / "cache"
MARKET_PREFIXES = ("yf_", "etf_profile_", "fundamentals_")


def clear() -> int:
    removed = 0
    for f in CACHE_DIR.glob("*.json"):
        if f.name.startswith(MARKET_PREFIXES):
            f.unlink(missing_ok=True)
            removed += 1
    return removed


def warm() -> None:
    from src.portfolio.store import list_portfolios, load_portfolio
    from src.portfolio.valuation import value_portfolio
    from src.portfolio.watchlist import load_watchlist

    symbols: set[str] = set()
    for p in list_portfolios():
        portfolio = load_portfolio(p["slug"])
        if portfolio is None:
            continue
        print(f"  {portfolio['name']}: pricing holdings...", flush=True)
        valuation = value_portfolio(portfolio)  # fetches fresh prices
        for h in portfolio.get("holdings", []):
            symbols.add(h["symbol"])
        for w in load_watchlist(p["slug"]):
            symbols.add(w["symbol"])
        if valuation.get("warnings"):
            for w in valuation["warnings"]:
                print(f"    ! {w}")

    from config.settings import get_compass_universe
    universe = {u["symbol"]: u for u in get_compass_universe()}

    for sym in sorted(symbols):
        meta = universe.get(sym)
        if meta is None:
            continue
        try:
            if meta["instrument_type"] == "etf" or meta["instrument_type"] == "crypto":
                from src.fetchers.etf_data import fetch_etf_profile
                fetch_etf_profile(sym, meta.get("yfinance", sym))
                print(f"  {sym}: profile refreshed")
            else:
                from src.analysis.fundamentals import fetch_fundamentals
                fetch_fundamentals(sym, meta.get("yfinance", sym))
                print(f"  {sym}: fundamentals refreshed")
        except Exception as e:
            print(f"  {sym}: skipped ({e})")


if __name__ == "__main__":
    print(f"Cleared {clear()} cached market-data files.")
    print("Re-warming everything the family's portfolios use:")
    warm()
    print("\nDone. To drop the running server's in-memory cache too:")
    print(f"  launchctl kickstart -k gui/{os.getuid()}/com.marketdigest.ui")
