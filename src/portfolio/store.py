"""Portfolio persistence — one JSON file per person under data/portfolios/.

No database by design (see CLAUDE.md). Writes are atomic (tempfile + os.replace).
"""

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
PORTFOLIO_DIR = PROJECT_ROOT / "data" / "portfolios"


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", name.strip().lower()).strip("-")
    if not slug:
        raise ValueError("Portfolio name must contain letters or numbers")
    return slug


def _path(name: str) -> Path:
    return PORTFOLIO_DIR / f"{_slug(name)}.json"


def list_portfolios() -> list[dict]:
    if not PORTFOLIO_DIR.exists():
        return []
    out = []
    for f in sorted(PORTFOLIO_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            out.append({
                "name": data.get("name", f.stem),
                "slug": f.stem,
                "holdings_count": len(data.get("holdings", [])),
                "cash": data.get("cash", 0),
                "updated": data.get("updated"),
            })
        except (json.JSONDecodeError, OSError):
            continue  # a corrupt file shouldn't hide the others
    return out


def load_portfolio(name: str) -> dict | None:
    path = _path(name)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_portfolio(data: dict) -> dict:
    data["updated"] = datetime.now().isoformat(timespec="seconds")
    PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
    path = _path(data["name"])
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return data


def create_portfolio(name: str) -> dict:
    if _path(name).exists():
        raise FileExistsError(f"A portfolio named '{name}' already exists")
    return save_portfolio({"name": name, "cash": 0.0, "holdings": [], "targets": {}})


def upsert_holding(name: str, symbol: str, shares: float, cost_basis: float,
                   account: str = "") -> dict:
    """Add or replace a holding. Symbol match is case-insensitive."""
    data = load_portfolio(name)
    if data is None:
        raise FileNotFoundError(name)
    symbol = symbol.strip().upper()
    holdings = [h for h in data["holdings"] if h["symbol"] != symbol]
    holdings.append({
        "symbol": symbol,
        "shares": round(float(shares), 6),
        "cost_basis": round(float(cost_basis), 4),
        "account": account.strip(),
    })
    data["holdings"] = sorted(holdings, key=lambda h: h["symbol"])
    return save_portfolio(data)


def delete_holding(name: str, symbol: str) -> dict:
    data = load_portfolio(name)
    if data is None:
        raise FileNotFoundError(name)
    symbol = symbol.strip().upper()
    data["holdings"] = [h for h in data["holdings"] if h["symbol"] != symbol]
    return save_portfolio(data)


def delete_portfolio(name: str) -> None:
    """Delete a portfolio and its watchlist. The file is gone for good."""
    path = _path(name)
    if not path.exists():
        raise FileNotFoundError(name)
    path.unlink()
    watchlist = PROJECT_ROOT / "data" / "watchlists" / f"{_slug(name)}.json"
    watchlist.unlink(missing_ok=True)


def set_cash(name: str, amount: float) -> dict:
    data = load_portfolio(name)
    if data is None:
        raise FileNotFoundError(name)
    data["cash"] = round(float(amount), 2)
    return save_portfolio(data)


# ── CSV import ──────────────────────────────────────────────────

_SYMBOL_COLS = {"symbol", "ticker", "stock"}
_SHARES_COLS = {"shares", "quantity", "qty", "share"}
_COST_COLS = {"cost_basis", "cost basis", "avg cost", "average cost", "avg price",
              "average price", "price", "cost", "purchase price"}


def parse_csv(text: str) -> tuple[list[dict], list[str]]:
    """Tolerant CSV parser for broker exports.

    Returns (holdings, skipped) where skipped is a list of human-readable
    reasons — the caller shows partial success rather than failing the import.
    """
    import csv
    import io

    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if any(c.strip() for c in r)]
    if not rows:
        return [], ["The file appears to be empty."]

    header = [c.strip().lower().lstrip("﻿") for c in rows[0]]

    def find_col(names: set[str]) -> int | None:
        for i, col in enumerate(header):
            if col in names:
                return i
        return None

    sym_i, sh_i, cost_i = find_col(_SYMBOL_COLS), find_col(_SHARES_COLS), find_col(_COST_COLS)
    if sym_i is None or sh_i is None:
        return [], [
            "Couldn't find the required columns. The file needs at least a "
            "'Symbol' (or 'Ticker') column and a 'Shares' (or 'Quantity') column."
        ]

    holdings, skipped = [], []
    for line_no, row in enumerate(rows[1:], start=2):
        try:
            symbol = row[sym_i].strip().upper()
            if not symbol or not re.match(r"^[A-Z.\-]{1,10}$", symbol):
                skipped.append(f"Row {line_no}: '{row[sym_i].strip()}' doesn't look like a ticker")
                continue
            shares = float(row[sh_i].replace(",", "").replace("$", "").strip())
            if shares <= 0:
                skipped.append(f"Row {line_no}: {symbol} has no shares")
                continue
            cost = 0.0
            if cost_i is not None and cost_i < len(row) and row[cost_i].strip():
                cost = float(row[cost_i].replace(",", "").replace("$", "").strip())
            holdings.append({"symbol": symbol, "shares": round(shares, 6),
                             "cost_basis": round(cost, 4), "account": ""})
        except (ValueError, IndexError):
            skipped.append(f"Row {line_no}: couldn't read the numbers on this row")
    return holdings, skipped


def import_holdings(name: str, holdings: list[dict]) -> dict:
    """Merge imported holdings into a portfolio (imported rows win on conflict)."""
    data = load_portfolio(name)
    if data is None:
        raise FileNotFoundError(name)
    imported_syms = {h["symbol"] for h in holdings}
    kept = [h for h in data["holdings"] if h["symbol"] not in imported_syms]
    data["holdings"] = sorted(kept + holdings, key=lambda h: h["symbol"])
    return save_portfolio(data)
