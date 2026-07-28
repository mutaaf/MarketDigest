"""Daily portfolio value history — one JSON file per portfolio.

Recorded by the weekday compass-daily job. Small forever: one row per day.
Powers the future performance-over-time chart.
"""

import json
import os
import tempfile
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
HISTORY_DIR = PROJECT_ROOT / "data" / "history"


def _path(slug: str) -> Path:
    return HISTORY_DIR / f"{slug}.json"


def get_history(slug: str) -> list[dict]:
    try:
        return json.loads(_path(slug).read_text())
    except (OSError, json.JSONDecodeError):
        return []


def record_snapshot(slug: str, valuation: dict) -> None:
    """Record today's value (idempotent — re-running a day overwrites that day)."""
    today = date.today().isoformat()
    rows = [r for r in get_history(slug) if r.get("date") != today]
    rows.append({
        "date": today,
        "total_value": valuation.get("total_value"),
        "invested_value": valuation.get("invested_value"),
        "cash": valuation.get("cash"),
    })
    rows.sort(key=lambda r: r["date"])
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    path = _path(slug)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(rows, f, indent=1)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def record_all() -> int:
    """Snapshot every portfolio. Returns how many were recorded."""
    from src.portfolio.store import list_portfolios, load_portfolio
    from src.portfolio.valuation import value_portfolio

    count = 0
    for p in list_portfolios():
        portfolio = load_portfolio(p["slug"])
        if portfolio is None:
            continue
        valuation = value_portfolio(portfolio)
        if valuation.get("total_value"):
            record_snapshot(p["slug"], valuation)
            count += 1
    return count
