"""Overlap analysis — do your funds (and stocks) own the same things?

Uses cached ETF top-10 holdings only, so it's instant and best-effort:
top-10 covers the concentrated overlaps that actually matter.
"""


def analyze_overlap(allocation: dict) -> dict:
    from src.cache.manager import CacheManager
    cache = CacheManager()

    etfs, stocks = [], []
    for h in allocation.get("by_holding", []):
        if not h.get("weight"):
            continue
        if h.get("instrument_type") == "etf":
            profile = cache.get_stale(f"etf_profile:{h['symbol']}")
            top = {t["symbol"]: t.get("weight") or 0
                   for t in (profile or {}).get("top_holdings", [])}
            etfs.append({"symbol": h["symbol"], "weight": h["weight"], "top": top})
        elif h.get("instrument_type") == "stock":
            stocks.append({"symbol": h["symbol"], "weight": h["weight"]})

    findings = []

    # Individual stocks you also own through your funds
    for s in stocks:
        holders = [(e["symbol"], e["top"][s["symbol"]]) for e in etfs if s["symbol"] in e["top"]]
        if holders:
            via = ", ".join(f"{sym} ({pct:.0f}% of that fund)" for sym, pct in holders)
            findings.append({
                "kind": "stock_in_fund",
                "symbols": [s["symbol"]] + [h[0] for h in holders],
                "text": f"You own {s['symbol']} directly and again inside {via} — "
                        f"a dip in {s['symbol']} hits you twice.",
            })

    # Fund pairs holding the same top names
    for i in range(len(etfs)):
        for j in range(i + 1, len(etfs)):
            a, b = etfs[i], etfs[j]
            shared = set(a["top"]) & set(b["top"])
            if not shared:
                continue
            overlap_pct = sum(min(a["top"][s], b["top"][s]) for s in shared)
            if overlap_pct >= 10:
                names = ", ".join(sorted(shared, key=lambda s: -min(a["top"][s], b["top"][s]))[:4])
                findings.append({
                    "kind": "fund_pair",
                    "symbols": [a["symbol"], b["symbol"]],
                    "overlap_pct": round(overlap_pct, 1),
                    "text": f"{a['symbol']} and {b['symbol']} hold many of the same companies "
                            f"({names}…) — owning both adds less variety than it looks.",
                })

    unanalyzed = [e["symbol"] for e in etfs if not e["top"]]
    return {
        "findings": findings,
        "note": ("Based on each fund's ten biggest holdings."
                 + (f" {', '.join(unanalyzed)} not analyzed yet — open it on the Explore page first."
                    if unanalyzed else "")),
    }
