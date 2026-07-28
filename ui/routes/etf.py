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
