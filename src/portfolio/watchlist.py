"""Watchlist — symbols to buy at the right price, one JSON file per portfolio."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
WATCHLIST_DIR = PROJECT_ROOT / "data" / "watchlists"


def _path(slug: str) -> Path:
    return WATCHLIST_DIR / f"{slug}.json"


def load_watchlist(slug: str) -> list[dict]:
    path = _path(slug)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def _save(slug: str, items: list[dict]) -> None:
    WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)
    path = _path(slug)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(items, f, indent=2)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def add_item(slug: str, symbol: str, buy_price: float | None, notes: str = "") -> list[dict]:
    symbol = symbol.strip().upper()
    items = [i for i in load_watchlist(slug) if i["symbol"] != symbol]
    items.append({
        "symbol": symbol,
        "buy_price": round(float(buy_price), 2) if buy_price else None,
        "notes": notes.strip(),
        "added": datetime.now().isoformat(timespec="seconds"),
    })
    items.sort(key=lambda i: i["symbol"])
    _save(slug, items)
    return items


def remove_item(slug: str, symbol: str) -> list[dict]:
    items = [i for i in load_watchlist(slug) if i["symbol"] != symbol.strip().upper()]
    _save(slug, items)
    return items


def enrich_watchlist(slug: str) -> dict:
    """Watchlist with live prices, distance-to-buy-price, and grades.
    Partial data with warnings, never a hard failure."""
    from config.settings import get_compass_universe
    from src.fetchers.yfinance_fetcher import YFinanceFetcher

    items = load_watchlist(slug)
    if not items:
        return {"items": [], "warnings": []}

    universe = {u["symbol"]: u for u in get_compass_universe()}
    prices = YFinanceFetcher().get_batch_prices([i["symbol"] for i in items])

    out, warnings = [], []
    for item in items:
        sym = item["symbol"]
        meta = universe.get(sym, {})
        p = prices.get(sym)
        enriched = {
            **item,
            "name": meta.get("name"),
            "type": meta.get("instrument_type"),
            "price": p["price"] if p else None,
            "day_change_pct": p.get("change_pct") if p else None,
            "grade": _cached_grade(sym, meta),
        }
        if p is None:
            warnings.append(f"Couldn't get a current price for {sym}.")
        if p and item.get("buy_price"):
            diff_pct = (p["price"] / item["buy_price"] - 1) * 100
            enriched["above_buy_pct"] = round(diff_pct, 1)
            enriched["at_buy_price"] = diff_pct <= 0
        out.append(enriched)
    return {"items": out, "warnings": warnings}


def _cached_grade(symbol: str, meta: dict) -> str | None:
    """Grade from already-cached data only — watchlist stays fast."""
    try:
        from src.analysis.daytrade_scorer import score_to_grade
        from src.cache.manager import CacheManager
        cache = CacheManager()
        if meta.get("instrument_type") == "etf":
            profile = cache.get_stale(f"etf_profile:{symbol}")
            if profile:
                from src.analysis.etf_scorer import score_etf
                return score_etf(profile, meta.get("category"))["grade"]
        else:
            fnd = cache.get_stale(f"fundamentals:v2:{symbol}")
            if fnd:
                from src.analysis.fundamentals import score_fundamentals
                return score_to_grade(score_fundamentals(fnd)["composite"])
    except Exception:
        pass
    return None
