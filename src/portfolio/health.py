"""Portfolio health — diversification factors, each with a plain-English explanation.

Every factor returns {name, score, status, detail} where status is
good / ok / warn and detail is written for a non-technical reader.
"""

from src.analysis.daytrade_scorer import score_to_grade


def _factor(name: str, score: float, detail: str) -> dict:
    status = "good" if score >= 70 else "ok" if score >= 45 else "warn"
    return {"name": name, "score": round(score, 1), "status": status, "detail": detail}


def _position_concentration(allocation: dict) -> dict:
    positions = [h for h in allocation.get("by_holding", []) if h.get("weight")]
    if not positions:
        return _factor("Single-position risk", 50, "Add holdings to see this check.")
    top = positions[0]
    w = top["weight"]
    name = top.get("display_name", top["symbol"])
    if top.get("instrument_type") == "etf" and w < 50:
        return _factor("Single-position risk", 90,
                       f"Your largest holding, {name}, is {w:.0f}% of your portfolio — "
                       "and since it's a fund holding many companies, that's fine.")
    if w <= 10:
        return _factor("Single-position risk", 95,
                       f"No single investment dominates — your largest, {name}, is only {w:.0f}%.")
    if w <= 20:
        return _factor("Single-position risk", 70,
                       f"{name} is {w:.0f}% of your portfolio. That's acceptable, but keep an eye on it.")
    if w <= 35:
        return _factor("Single-position risk", 45,
                       f"{name} is {w:.0f}% of your portfolio. If it has a bad year, "
                       "your whole portfolio feels it. Consider trimming or diversifying around it.")
    return _factor("Single-position risk", 20,
                   f"{name} is {w:.0f}% of your portfolio — that's a lot riding on one investment.")


def _sector_concentration(allocation: dict) -> dict:
    sectors = [s for s in allocation.get("sectors", []) if s["key"] != "Diversified fund"]
    if not sectors:
        return _factor("Sector balance", 60,
                       "We couldn't break your funds into sectors yet — this fills in "
                       "as fund data loads.")
    top = sectors[0]
    w = top["weight"]
    if w <= 25:
        return _factor("Sector balance", 90,
                       f"Nicely spread across industries — {top['label']} is your largest at {w:.0f}%.")
    if w <= 40:
        return _factor("Sector balance", 60,
                       f"{top['label']} makes up {w:.0f}% of your stocks. A downturn in that "
                       "industry would hit you harder than most.")
    return _factor("Sector balance", 30,
                   f"{top['label']} is {w:.0f}% of your portfolio — that's heavily "
                   "concentrated in one industry.")


def _asset_class_spread(allocation: dict) -> dict:
    classes = {c["key"]: c["weight"] for c in allocation.get("asset_classes", [])}
    meaningful = [k for k, w in classes.items() if w >= 5 and k not in ("cash", "other")]
    n = len(meaningful)
    if n >= 3:
        return _factor("Mix of asset types", 90,
                       "You own a healthy mix of asset types (stocks, bonds, or real "
                       "estate), which smooths out rough markets.")
    if n == 2:
        return _factor("Mix of asset types", 65,
                       "You hold two main types of assets. Adding a third — like bonds "
                       "or real estate — can steady the ride.")
    return _factor("Mix of asset types", 40,
                   "Nearly everything you own is one type of asset. Mixing in bonds or "
                   "other assets cushions bad years for stocks.")


def _international_exposure(allocation: dict) -> dict:
    classes = {c["key"]: c["weight"] for c in allocation.get("asset_classes", [])}
    intl = classes.get("intl_stock", 0)
    stocks_total = intl + classes.get("us_stock", 0)
    if stocks_total < 5:
        return _factor("US vs international", 60, "Not enough stock holdings to judge this yet.")
    share = intl / stocks_total * 100
    if 15 <= share <= 45:
        return _factor("US vs international", 90,
                       f"About {share:.0f}% of your stocks are international — a healthy balance.")
    if 5 <= share < 15:
        return _factor("US vs international", 60,
                       f"Only {share:.0f}% of your stocks are outside the US. Many advisors "
                       "suggest 20-40% international.")
    if share < 5:
        return _factor("US vs international", 35,
                       "Almost all your stocks are US companies. International funds (like "
                       "VXUS) spread your bets across world markets.")
    return _factor("US vs international", 55,
                   f"{share:.0f}% of your stocks are international — on the high side; "
                   "most long-term plans keep the US as the anchor.")


def _effective_holdings(allocation: dict) -> dict:
    weights = [h["weight"] / 100 for h in allocation.get("by_holding", []) if h.get("weight")]
    if not weights:
        return _factor("Number of holdings", 50, "Add holdings to see this check.")
    hhi = sum(w * w for w in weights)
    effective_n = 1 / hhi if hhi > 0 else 0
    has_broad_fund = any(h.get("instrument_type") == "etf"
                         for h in allocation.get("by_holding", []))
    if has_broad_fund or effective_n >= 10:
        return _factor("Number of holdings", 90,
                       "Between funds and individual positions, your money is spread "
                       "across plenty of companies.")
    if effective_n >= 5:
        return _factor("Number of holdings", 65,
                       f"Your portfolio behaves like about {effective_n:.0f} equally-sized "
                       "bets. More spread would reduce single-company risk.")
    return _factor("Number of holdings", 35,
                   f"Your portfolio behaves like only about {effective_n:.0f} bets. A broad "
                   "index fund instantly diversifies you across hundreds of companies.")


def assess_health(allocation: dict, valuation: dict) -> dict:
    """Overall portfolio health: factor list, diversification score, letter grade."""
    if not valuation.get("holdings") and not valuation.get("cash"):
        return {"grade": None, "score": None, "factors": [],
                "summary": "Add your first holding to get a health check."}

    factors = [
        _position_concentration(allocation),
        _sector_concentration(allocation),
        _asset_class_spread(allocation),
        _international_exposure(allocation),
        _effective_holdings(allocation),
    ]
    score = round(sum(f["score"] for f in factors) / len(factors), 1)
    grade = score_to_grade(score)

    warns = [f for f in factors if f["status"] == "warn"]
    if not warns:
        summary = "Your portfolio is well diversified. Keep doing what you're doing."
    elif len(warns) == 1:
        summary = f"One thing to look at: {warns[0]['name'].lower()}."
    else:
        summary = f"{len(warns)} areas could use attention — see the checks below."

    return {"grade": grade, "score": score, "factors": factors, "summary": summary}
