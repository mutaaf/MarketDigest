"""Allocation analysis — asset class, sector (with ETF look-through), costs.

Uses instruments.yaml metadata for classification and cached ETF profiles for
sector look-through. Unknown symbols land in 'Other' rather than erroring.
"""

from config.settings import get_settings

ASSET_CLASS_LABELS = {
    "us_stock": "US Stocks",
    "intl_stock": "International",
    "bond": "Bonds",
    "reit": "Real Estate",
    "commodity": "Commodities",
    "crypto": "Crypto",
    "cash": "Cash",
    "other": "Other",
}


def _universe_index() -> dict[str, dict]:
    """symbol -> {instrument_type, asset_class, sector, name} for stocks + ETFs."""
    instruments = get_settings().instruments
    index = {}
    for s in instruments.get("us_stocks", []):
        index[s["symbol"]] = {
            "instrument_type": "stock",
            "asset_class": s.get("asset_class", "us_stock"),
            "sector": s.get("sector"),
            "name": s.get("name", s["symbol"]),
        }
    for e in instruments.get("etfs", []):
        index[e["symbol"]] = {
            "instrument_type": "etf",
            "asset_class": e.get("asset_class", "other"),
            "category": e.get("category"),
            "sector": None,
            "name": e.get("name", e["symbol"]),
        }
    return index


def analyze_allocation(valuation: dict) -> dict:
    """Break the valued portfolio into asset-class and sector weights.

    ETF sector look-through uses cached ETF profiles only (no live fetches here);
    ETFs without a cached profile contribute to sector 'Diversified fund'.
    """
    from src.cache.manager import CacheManager
    cache = CacheManager()
    index = _universe_index()

    total = valuation.get("total_value") or 0
    if total <= 0:
        return {"asset_classes": [], "sectors": [], "by_holding": [],
                "weighted_expense_ratio": None, "unclassified": []}

    asset_class_totals: dict[str, float] = {}
    sector_totals: dict[str, float] = {}
    by_holding = []
    unclassified = []
    expense_weighted = 0.0
    expense_covered = 0.0

    cash = valuation.get("cash", 0)
    if cash > 0:
        asset_class_totals["cash"] = cash

    for h in valuation.get("holdings", []):
        value = h.get("value")
        if not value:
            continue
        meta = index.get(h["symbol"])
        if meta is None:
            unclassified.append(h["symbol"])
            asset_class_totals["other"] = asset_class_totals.get("other", 0) + value
            by_holding.append({**h, "weight": round(value / total * 100, 2),
                               "asset_class": "other", "instrument_type": "unknown"})
            continue

        ac = meta["asset_class"]
        asset_class_totals[ac] = asset_class_totals.get(ac, 0) + value
        by_holding.append({**h, "weight": round(value / total * 100, 2),
                           "asset_class": ac,
                           "instrument_type": meta["instrument_type"],
                           "display_name": meta["name"]})

        if meta["instrument_type"] == "stock":
            sector = meta.get("sector") or "Other"
            sector_totals[sector] = sector_totals.get(sector, 0) + value
        else:
            profile = cache.get_stale(f"etf_profile:{h['symbol']}")
            weights = (profile or {}).get("sector_weights") or {}
            if weights and ac in ("us_stock", "intl_stock"):
                for sector_key, pct in weights.items():
                    label = _sector_label(sector_key)
                    sector_totals[label] = sector_totals.get(label, 0) + value * pct / 100
            elif ac in ("us_stock", "intl_stock"):
                sector_totals["Diversified fund"] = sector_totals.get("Diversified fund", 0) + value
            er = (profile or {}).get("expense_ratio")
            if er is not None:
                expense_weighted += er * value
                expense_covered += value

    def as_list(totals: dict, labels: dict | None = None) -> list[dict]:
        items = [{"key": k,
                  "label": (labels or {}).get(k, k),
                  "value": round(v, 2),
                  "weight": round(v / total * 100, 2)}
                 for k, v in totals.items()]
        return sorted(items, key=lambda x: -x["weight"])

    return {
        "asset_classes": as_list(asset_class_totals, ASSET_CLASS_LABELS),
        "sectors": as_list(sector_totals),
        "by_holding": sorted(by_holding, key=lambda x: -(x.get("weight") or 0)),
        "weighted_expense_ratio": round(expense_weighted / expense_covered, 3) if expense_covered > 0 else None,
        "unclassified": unclassified,
    }


_SECTOR_LABELS = {
    "technology": "Technology",
    "financial_services": "Financial Services",
    "healthcare": "Healthcare",
    "consumer_cyclical": "Consumer Cyclical",
    "consumer_defensive": "Consumer Defensive",
    "communication_services": "Communication Services",
    "industrials": "Industrials",
    "energy": "Energy",
    "utilities": "Utilities",
    "basic_materials": "Basic Materials",
    "realestate": "Real Estate",
}


def _sector_label(key: str) -> str:
    return _SECTOR_LABELS.get(key, key.replace("_", " ").title())
