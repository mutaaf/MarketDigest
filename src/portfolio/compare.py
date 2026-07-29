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


def compare(symbol_a: str, symbol_b: str) -> dict:
    a = _load_side(symbol_a)
    b = _load_side(symbol_b)
    missing = [s for s, side in [(symbol_a, a), (symbol_b, b)] if side is None]
    if missing:
        return {"error": f"Couldn't load data for {' and '.join(m.upper() for m in missing)}. "
                         "Check the ticker symbol and try again.",
                "a": a, "b": b}
    return {"a": a, "b": b, "verdict": _verdict(a, b)}
