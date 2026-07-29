"""ETF database API — list, profile, scores."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/etf", tags=["etf"])


@router.get("/list")
async def list_etfs():
    """All enabled ETFs from config, with scores for any already-cached profiles.
    Never triggers live fetches — this endpoint stays fast."""
    from config.settings import get_etf_universe
    from src.analysis.etf_scorer import score_etf
    from src.cache.manager import CacheManager

    cache = CacheManager()
    out = []
    for etf in get_etf_universe():
        entry = {
            "symbol": etf["symbol"],
            "name": etf["name"],
            "category": etf["category"],
            "asset_class": etf["asset_class"],
            "cached": False,
        }
        profile = cache.get(f"etf_profile:{etf['symbol']}", max_age_seconds=24 * 3600)
        if profile:
            scored = score_etf(profile, etf["category"])
            entry.update({
                "cached": True,
                "expense_ratio": profile.get("expense_ratio"),
                "dividend_yield": profile.get("dividend_yield"),
                "return_5y": profile.get("return_5y"),
                "grade": scored["grade"],
                "overall": scored["overall"],
                "risk_level": scored["risk_level"],
            })
        out.append(entry)
    return {"etfs": out}


@router.get("/{symbol}/insights")
async def etf_insights(symbol: str):
    """LLM-written pros / cons / best-for plus similar funds (same category,
    grade-ranked). Insights cache for 7 days — funds don't change character fast."""
    import json
    import re

    from config.settings import get_etf_universe, get_settings
    from src.analysis.etf_scorer import score_etf
    from src.cache.manager import CacheManager
    from src.fetchers.etf_data import fetch_etf_profile

    symbol = symbol.upper()
    cache = CacheManager()
    cache_key = f"etf_insights:{symbol}"
    cached = cache.get(cache_key, max_age_seconds=7 * 86400)

    config = next((e for e in get_etf_universe() if e["symbol"] == symbol), None)

    # Similar funds: same category, best grades first (cached profiles only)
    similar = []
    if config:
        for e in get_etf_universe():
            if e["symbol"] == symbol or e["category"] != config["category"]:
                continue
            profile = cache.get_stale(f"etf_profile:{e['symbol']}")
            overall = score_etf(profile, e["category"])["overall"] if profile else -1
            similar.append({"symbol": e["symbol"], "name": e["name"], "_o": overall})
        similar.sort(key=lambda s: -s["_o"])
        similar = [{k: v for k, v in s.items() if k != "_o"} for s in similar[:4]]

    if cached is not None:
        return {**cached, "similar": similar}

    if not get_settings().has_llm_key():
        return {"pros": [], "cons": [], "best_for": None, "similar": similar,
                "note": "Pros & cons need an AI key — add one on Settings."}

    profile = fetch_etf_profile(symbol, (config or {}).get("yfinance", symbol))
    if profile is None:
        raise HTTPException(status_code=502, detail=f"Couldn't load {symbol} right now.")
    scored = score_etf(profile, (config or {}).get("category"))

    from src.analysis.llm_providers import LLMProvider
    prompt = (
        f"Fund: {profile.get('name')} ({symbol}), category {(config or {}).get('category')}. "
        f"Expense ratio {profile.get('expense_ratio')}%, yield {profile.get('dividend_yield')}%, "
        f"5y return {profile.get('return_5y')}%/yr, 10y {profile.get('return_10y')}%/yr, "
        f"volatility {profile.get('volatility_1y')}%, AUM ${profile.get('aum')}, "
        f"grade {scored['grade']}, risk {scored['risk_level']}.\n"
        'Respond with ONLY JSON: {"pros": ["...", "..."], "cons": ["...", "..."], '
        '"best_for": "one sentence"}. 2-3 pros, 2-3 cons, each under 15 words, '
        "plain English for a beginner, grounded in the numbers given. Be honest about cons."
    )
    result = LLMProvider().generate(
        "You write honest, beginner-friendly fund summaries for a family investing app.",
        prompt, max_tokens=350)
    if result is None:
        return {"pros": [], "cons": [], "best_for": None, "similar": similar,
                "note": "Couldn't reach the AI right now — try again in a minute."}

    try:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", result.text.strip(), flags=re.MULTILINE)
        data = json.loads(cleaned)
        insights = {"pros": [str(p) for p in data.get("pros", [])][:3],
                    "cons": [str(c) for c in data.get("cons", [])][:3],
                    "best_for": str(data.get("best_for", "")) or None}
    except (json.JSONDecodeError, AttributeError):
        insights = {"pros": [], "cons": [], "best_for": result.text.strip()[:200]}

    cache.set(cache_key, insights)
    return {**insights, "similar": similar}


@router.get("/{symbol}")
async def get_etf(symbol: str):
    """Full ETF profile + scores. Fetches live (then 24h-cached)."""
    from config.settings import get_etf_universe
    from src.analysis.etf_scorer import score_etf
    from src.fetchers.etf_data import fetch_etf_profile

    symbol = symbol.upper()
    config = next((e for e in get_etf_universe() if e["symbol"] == symbol), None)

    profile = fetch_etf_profile(symbol, (config or {}).get("yfinance", symbol))
    if profile is None:
        raise HTTPException(
            status_code=502,
            detail=f"Could not load data for {symbol} right now. Try again in a minute.",
        )

    scored = score_etf(profile, (config or {}).get("category"))
    return {
        **profile,
        **scored,
        "category": (config or {}).get("category"),
        "asset_class": (config or {}).get("asset_class"),
        "in_universe": config is not None,
    }
