"""Family-facing 'pull the latest' — clear market caches and re-warm.

Rate-limited to once every 5 minutes globally (data providers don't move
faster than that, and it keeps a tap-happy family member from hammering
yfinance). Clears BOTH file cache and this process's memory cache.
"""

import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
CACHE_DIR = PROJECT_ROOT / "cache"
STAMP = CACHE_DIR / "last_family_refresh.txt"

COOLDOWN_SECONDS = 5 * 60
FILE_PREFIXES = ("yf_", "etf_profile_", "fundamentals_")
MEMORY_PREFIXES = ("yf_", "etf_profile:", "fundamentals:")


def seconds_until_allowed() -> int:
    try:
        last = float(STAMP.read_text().strip())
    except (OSError, ValueError):
        return 0
    return max(0, int(COOLDOWN_SECONDS - (time.time() - last)))


def clear_market_caches() -> int:
    from src.cache.manager import CacheManager
    removed = 0
    for f in CACHE_DIR.glob("*.json"):
        if f.name.startswith(FILE_PREFIXES):
            f.unlink(missing_ok=True)
            removed += 1
    CacheManager.clear_memory_prefixes(MEMORY_PREFIXES)
    return removed


def warm_portfolio(slug: str) -> list[str]:
    """Re-fetch prices + profiles/fundamentals for one portfolio's holdings
    and watchlist. Returns warnings (partial results, never a failure)."""
    from config.settings import get_compass_universe
    from src.portfolio.store import load_portfolio
    from src.portfolio.valuation import value_portfolio
    from src.portfolio.watchlist import load_watchlist

    portfolio = load_portfolio(slug)
    if portfolio is None:
        return [f"Portfolio '{slug}' not found."]

    valuation = value_portfolio(portfolio)  # fresh prices
    warnings = list(valuation.get("warnings", []))

    symbols = {h["symbol"] for h in portfolio.get("holdings", [])}
    symbols |= {w["symbol"] for w in load_watchlist(slug)}
    universe = {u["symbol"]: u for u in get_compass_universe()}

    for sym in sorted(symbols):
        meta = universe.get(sym)
        if meta is None:
            continue
        try:
            if meta["instrument_type"] in ("etf", "crypto"):
                from src.fetchers.etf_data import fetch_etf_profile
                fetch_etf_profile(sym, meta.get("yfinance", sym))
            else:
                from src.analysis.fundamentals import fetch_fundamentals
                fetch_fundamentals(sym, meta.get("yfinance", sym))
        except Exception:
            warnings.append(f"Couldn't refresh {sym} — it'll retry on next view.")
    return warnings


def family_refresh(slug: str | None) -> dict:
    """The endpoint's workhorse: cooldown check, clear, warm."""
    wait = seconds_until_allowed()
    if wait > 0:
        return {"ok": False, "seconds_until_next": wait}

    CACHE_DIR.mkdir(exist_ok=True)
    STAMP.write_text(str(time.time()))
    cleared = clear_market_caches()
    warnings = warm_portfolio(slug) if slug else []
    return {"ok": True, "cleared": cleared, "warnings": warnings,
            "seconds_until_next": COOLDOWN_SECONDS}
