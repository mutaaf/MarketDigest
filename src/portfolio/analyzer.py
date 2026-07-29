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
    for c in instruments.get("crypto", []):
        index[c["symbol"]] = {
            "instrument_type": "crypto",
            "asset_class": "crypto",
            "sector": None,
            "name": c.get("name", c["symbol"]),
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
        # Nothing priced yet — still list the holdings so they don't vanish
        unpriced = [{**h, "weight": 0.0,
                     "asset_class": (index.get(h["symbol"]) or {}).get("asset_class", "other"),
                     "instrument_type": (index.get(h["symbol"]) or {}).get("instrument_type", "unknown"),
                     "display_name": (index.get(h["symbol"]) or {}).get("name")}
                    for h in valuation.get("holdings", [])]
        return {"asset_classes": [], "sectors": [], "by_holding": unpriced,
                "weighted_expense_ratio": None, "unclassified": []}

    asset_class_totals: dict[str, float] = {}
    sector_totals: dict[str, float] = {}
    geo_totals: dict[str, float] = {}
    cap_totals: dict[str, float] = {}
    style_totals: dict[str, float] = {}
    by_holding = []
    unclassified = []
    expense_weighted = 0.0
    expense_covered = 0.0
    beta_weighted = 0.0
    beta_covered = 0.0
    yield_weighted = 0.0
    yield_covered = 0.0

    cash = valuation.get("cash", 0)
    if cash > 0:
        asset_class_totals["cash"] = cash

    for h in valuation.get("holdings", []):
        value = h.get("value")
        meta = index.get(h["symbol"])
        if not value:
            # Unpriced holdings still belong in the list — weight 0, no totals impact
            by_holding.append({**h, "weight": 0.0,
                               "asset_class": (meta or {}).get("asset_class", "other"),
                               "instrument_type": (meta or {}).get("instrument_type", "unknown"),
                               "display_name": (meta or {}).get("name")})
            continue
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

        geo = _geography(ac, meta.get("category"))
        geo_totals[geo] = geo_totals.get(geo, 0) + value

        if meta["instrument_type"] == "crypto":
            cap_totals["Not stocks"] = cap_totals.get("Not stocks", 0) + value
        elif meta["instrument_type"] == "stock":
            sector = meta.get("sector") or "Other"
            sector_totals[sector] = sector_totals.get(sector, 0) + value
            fnd = cache.get_stale(f"fundamentals:v2:{h['symbol']}") or {}
            metrics = fnd.get("metrics", {})
            cap = _cap_bucket_from_value(fnd.get("market_cap"))
            cap_totals[cap] = cap_totals.get(cap, 0) + value
            style_totals["Blend"] = style_totals.get("Blend", 0) + value
            if metrics.get("beta") is not None:
                beta_weighted += metrics["beta"] * value
                beta_covered += value
            if metrics.get("dividend_yield") is not None:
                yield_weighted += metrics["dividend_yield"] * value
                yield_covered += value
        else:
            profile = cache.get_stale(f"etf_profile:{h['symbol']}")
            weights = (profile or {}).get("sector_weights") or {}
            if weights and ac in ("us_stock", "intl_stock"):
                for sector_key, pct in weights.items():
                    label = _sector_label(sector_key)
                    sector_totals[label] = sector_totals.get(label, 0) + value * pct / 100
            elif ac in ("us_stock", "intl_stock"):
                sector_totals["Diversified fund"] = sector_totals.get("Diversified fund", 0) + value
            cap = _cap_bucket_from_category(meta.get("category"), ac)
            cap_totals[cap] = cap_totals.get(cap, 0) + value
            style = _style_from_category(meta.get("category"))
            style_totals[style] = style_totals.get(style, 0) + value
            er = (profile or {}).get("expense_ratio")
            if er is not None:
                expense_weighted += er * value
                expense_covered += value
            if (profile or {}).get("beta_3y") is not None:
                beta_weighted += profile["beta_3y"] * value
                beta_covered += value
            elif ac == "bond":
                beta_weighted += 0.1 * value  # bonds barely move with stocks
                beta_covered += value
            if (profile or {}).get("dividend_yield") is not None:
                yield_weighted += profile["dividend_yield"] * value
                yield_covered += value

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
        "geography": as_list(geo_totals),
        "market_caps": as_list(cap_totals),
        "styles": as_list(style_totals),
        "by_holding": sorted(by_holding, key=lambda x: -(x.get("weight") or 0)),
        "weighted_expense_ratio": round(expense_weighted / expense_covered, 3) if expense_covered > 0 else None,
        "weighted_beta": round(beta_weighted / beta_covered, 2)
        if beta_covered > (valuation.get("invested_value") or 0) * 0.5 else None,
        "weighted_yield": round(yield_weighted / yield_covered, 2)
        if yield_covered > (valuation.get("invested_value") or 0) * 0.5 else None,
        "unclassified": unclassified,
    }


def _geography(asset_class: str, category: str | None) -> str:
    if asset_class in ("us_stock", "reit"):
        return "United States"
    if asset_class == "intl_stock":
        if category == "intl_emerging":
            return "Emerging markets"
        if category == "intl_developed":
            return "Developed international"
        return "International mix"
    if asset_class == "bond":
        return "Bonds (mostly US)" if category != "bond_intl" else "International bonds"
    if asset_class == "crypto":
        return "Crypto (global)"
    return "Global / other"


def _cap_bucket_from_value(market_cap) -> str:
    if not market_cap:
        return "Unknown size"
    if market_cap >= 10e9:
        return "Large companies"
    if market_cap >= 2e9:
        return "Mid-size companies"
    return "Small companies"


def _cap_bucket_from_category(category: str | None, asset_class: str) -> str:
    if asset_class not in ("us_stock", "intl_stock"):
        return "Not stocks"
    if category in ("us_small",):
        return "Small companies"
    if category in ("us_mid",):
        return "Mid-size companies"
    return "Large companies"  # broad/large funds are overwhelmingly large-cap


def _style_from_category(category: str | None) -> str:
    if category in ("us_large_growth",):
        return "Growth"
    if category in ("us_large_value",):
        return "Value"
    if category in ("dividend", "covered_call"):
        return "Dividend"
    return "Blend"


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
