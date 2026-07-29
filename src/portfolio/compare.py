"""Two-ticker comparison — normalizes any mix of ETF/stock into one metric table
with a deterministic plain-English verdict."""


def _load_side(symbol: str) -> dict | None:
    from config.settings import get_settings
    from src.analysis.etf_scorer import score_etf
    from src.analysis.fundamentals import fetch_fundamentals, score_fundamentals
    from src.fetchers.etf_data import fetch_etf_profile

    symbol = symbol.upper()
    instruments = get_settings().instruments
    etf_cfg = next((e for e in instruments.get("etfs", []) if e["symbol"] == symbol), None)
    stock_cfg = next(
        (s for group in ("us_stocks", "compass_stocks")
         for s in instruments.get(group, []) if s["symbol"] == symbol),
        None,
    )
    crypto_cfg = next((c for c in instruments.get("crypto", [])
                       if c["symbol"] == symbol), None)

    if crypto_cfg:
        # Crypto gets prices/returns/volatility but deliberately NO grade —
        # our quality scores don't apply to it.
        profile = fetch_etf_profile(symbol, crypto_cfg.get("yfinance", f"{symbol}-USD"))
        if profile is None:
            return None
        return {
            "symbol": symbol,
            "name": crypto_cfg.get("name", symbol),
            "type": "crypto",
            "grade": None,
            "score": None,
            "risk_level": "Very High",
            "sub_scores": {},
            "metrics": {
                "current_price": profile.get("price"),
                "return_1y": profile.get("return_1y"),
                "return_5y": profile.get("return_5y"),
                "volatility_1y": profile.get("volatility_1y"),
            },
        }

    if etf_cfg or not stock_cfg:
        profile = fetch_etf_profile(symbol, (etf_cfg or {}).get("yfinance", symbol))
        if profile is None or (not etf_cfg and profile.get("expense_ratio") is None
                               and not profile.get("top_holdings")):
            profile = None
        if profile is not None:
            scored = score_etf(profile, (etf_cfg or {}).get("category"))
            return {
                "symbol": symbol,
                "name": profile.get("name") or (etf_cfg or {}).get("name", symbol),
                "type": "etf",
                "grade": scored["grade"],
                "score": scored["overall"],
                "risk_level": scored["risk_level"],
                "sub_scores": scored["scores"],
                "metrics": {
                    "expense_ratio": profile.get("expense_ratio"),
                    "dividend_yield": profile.get("dividend_yield"),
                    "return_1y": profile.get("return_1y"),
                    "return_5y": profile.get("return_5y"),
                    "return_10y": profile.get("return_10y"),
                    "volatility_1y": profile.get("volatility_1y"),
                    "aum": profile.get("aum"),
                },
                "top_holdings": profile.get("top_holdings", [])[:10],
            }

    if stock_cfg:
        fnd = fetch_fundamentals(symbol, stock_cfg.get("yfinance", symbol))
        if fnd is None:
            return None
        from src.analysis.daytrade_scorer import score_to_grade as grade_fn
        scores = score_fundamentals(fnd)
        m = fnd.get("metrics", {})
        return {
            "symbol": symbol,
            "name": stock_cfg.get("name", symbol),
            "type": "stock",
            "grade": grade_fn(scores["composite"]),
            "score": scores["composite"],
            "sector": fnd.get("sector") or stock_cfg.get("sector"),
            "sub_scores": {k: v for k, v in scores.items() if k != "composite"},
            "metrics": {
                "pe_ratio": m.get("pe_ratio"),
                "forward_pe": m.get("forward_pe"),
                "peg_ratio": m.get("peg_ratio"),
                "dividend_yield": m.get("dividend_yield"),
                "revenue_growth": m.get("revenue_growth"),
                "net_margin": m.get("net_margin"),
                "debt_equity": m.get("debt_equity"),
                "analyst_target": m.get("analyst_target"),
                "current_price": m.get("current_price"),
                "market_cap": fnd.get("market_cap"),
            },
        }
    return None


def _verdict(a: dict, b: dict) -> str:
    """A short, honest comparison summary — no LLM, always available."""
    if a.get("score") is None or b.get("score") is None:
        crypto = a if a.get("type") == "crypto" else b
        other = b if crypto is a else a
        vol = crypto["metrics"].get("volatility_1y")
        return (f"{crypto['symbol']} and {other['symbol']} play different roles: crypto is a "
                f"high-risk satellite ({f'{vol:.0f}% volatility — several times a broad fund' if vol else 'far more volatile than funds'}), "
                f"not a substitute for a portfolio's core. A common rule keeps crypto under ~5% of the total.")
    points = []
    if a["type"] == "etf" and b["type"] == "etf":
        ma, mb = a["metrics"], b["metrics"]
        er_a, er_b = ma.get("expense_ratio"), mb.get("expense_ratio")
        if er_a is not None and er_b is not None and abs(er_a - er_b) >= 0.02:
            cheap = a if er_a < er_b else b
            points.append(f"{cheap['symbol']} is cheaper to own")
        r_a, r_b = ma.get("return_5y"), mb.get("return_5y")
        if r_a is not None and r_b is not None and abs(r_a - r_b) >= 1:
            higher = a if r_a > r_b else b
            points.append(f"{higher['symbol']} has grown faster over five years")
        v_a, v_b = ma.get("volatility_1y"), mb.get("volatility_1y")
        if v_a is not None and v_b is not None and abs(v_a - v_b) >= 3:
            calmer = a if v_a < v_b else b
            points.append(f"{calmer['symbol']} has a smoother ride")
    if abs(a["score"] - b["score"]) < 3:
        lead = "They score nearly the same overall"
    else:
        best = a if a["score"] > b["score"] else b
        lead = f"{best['symbol']} scores higher overall ({best['grade']} vs " \
               f"{(b if best is a else a)['grade']})"
    if points:
        return f"{lead}. {'; '.join(points)}. Both can be reasonable long-term choices — " \
               "the better fit depends on what your portfolio is missing."
    return f"{lead}. The better fit depends on what your portfolio is missing."


def _for_you(a: dict, b: dict, slug: str) -> dict | None:
    """Personalized decision help: which side serves THIS portfolio better."""
    from config.settings import get_compass_universe
    from src.portfolio.analyzer import ASSET_CLASS_LABELS, analyze_allocation
    from src.portfolio.recommender import DEFAULT_TARGETS
    from src.portfolio.store import load_portfolio
    from src.portfolio.valuation import value_portfolio

    portfolio = load_portfolio(slug)
    if portfolio is None:
        return None
    valuation = value_portfolio(portfolio)
    if not valuation.get("total_value"):
        return None
    allocation = analyze_allocation(valuation)
    held = {h["symbol"]: h.get("weight") or 0 for h in allocation["by_holding"]}
    targets = {**DEFAULT_TARGETS, **(portfolio.get("targets") or {})}
    actual = {c["key"]: c["weight"] for c in allocation["asset_classes"]}
    universe = {u["symbol"]: u for u in get_compass_universe()}

    def info(side: dict) -> dict:
        sym = side["symbol"]
        ac = (universe.get(sym) or {}).get("asset_class")
        return {
            "asset_class": ac,
            "gap": round(targets.get(ac, 0) - actual.get(ac, 0), 1) if ac else 0.0,
            "owned_pct": round(held.get(sym, 0), 1),
        }

    ia, ib = info(a), info(b)
    points = []
    for side, i in ((a, ia), (b, ib)):
        if i["owned_pct"] > 0:
            points.append(f"You already own {side['symbol']} — it's {i['owned_pct']:.0f}% "
                          f"of your portfolio.")
        dup = [h["symbol"] for h in side.get("top_holdings", []) if held.get(h["symbol"])]
        if dup:
            points.append(f"{side['symbol']}'s biggest holdings include "
                          f"{', '.join(dup[:3])} — which you already own directly.")

    # Pair overlap when both are funds with known holdings
    near_dupes = False
    if a.get("top_holdings") and b.get("top_holdings"):
        ta = {h["symbol"]: h.get("weight") or 0 for h in a["top_holdings"]}
        tb = {h["symbol"]: h.get("weight") or 0 for h in b["top_holdings"]}
        pair_overlap = sum(min(ta[s], tb[s]) for s in set(ta) & set(tb))
        if pair_overlap >= 15 and ia["asset_class"] == ib["asset_class"]:
            near_dupes = True
            points.append(f"These two overlap heavily (~{pair_overlap:.0f}% shared top "
                          "holdings) — owning both adds little variety. Pick one.")

    # The decision
    pick, headline = None, ""
    label = lambda ac: ASSET_CLASS_LABELS.get(ac or "", ac or "either")  # noqa: E731
    if abs(ia["gap"] - ib["gap"]) > 3 and max(ia["gap"], ib["gap"]) > 2:
        winner, wi = (a, ia) if ia["gap"] > ib["gap"] else (b, ib)
        pick = winner["symbol"]
        headline = (f"{pick} fits your portfolio better right now — you're "
                    f"{wi['gap']:.0f} points under your {label(wi['asset_class'])} target "
                    f"({actual.get(wi['asset_class'], 0):.0f}% vs {targets.get(wi['asset_class'], 0):.0f}%).")
    elif near_dupes:
        owned = a if ia["owned_pct"] > 0 else b if ib["owned_pct"] > 0 else None
        if owned is not None:
            pick = owned["symbol"]
            headline = f"Near-duplicates — sticking with the {pick} you already own keeps things simple."
        else:
            best = a if a["score"] >= b["score"] else b
            pick = best["symbol"]
            headline = f"Near-duplicates — {pick} edges it on overall grade; you only need one."
    elif a.get("score") is not None and b.get("score") is not None and abs(a["score"] - b["score"]) >= 3:
        best = a if a["score"] > b["score"] else b
        pick = best["symbol"]
        headline = f"Neither fills a bigger gap for you, so quality decides: {pick} grades higher."
    else:
        headline = ("For your portfolio these are effectively interchangeable — "
                    "either works; cost and taste can decide.")

    return {"pick": pick, "headline": headline, "points": points[:4]}


def compare(symbol_a: str, symbol_b: str, portfolio: str | None = None) -> dict:
    a = _load_side(symbol_a)
    b = _load_side(symbol_b)
    missing = [s for s, side in [(symbol_a, a), (symbol_b, b)] if side is None]
    if missing:
        return {"error": f"Couldn't load data for {' and '.join(m.upper() for m in missing)}. "
                         "Check the ticker symbol and try again.",
                "a": a, "b": b}
    result = {"a": a, "b": b, "verdict": _verdict(a, b)}
    if portfolio:
        try:
            result["for_you"] = _for_you(a, b, portfolio)
        except Exception:
            result["for_you"] = None  # personalization is a bonus, never a blocker
    return result
