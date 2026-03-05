"""Options flow API endpoints."""

import time

import yaml
from fastapi import APIRouter, HTTPException

from config.settings import get_settings

router = APIRouter(prefix="/api/options", tags=["options"])

# Route-level cache (10 min TTL)
_CACHE_TTL = 600
_flow_cache: dict[str, dict] = {}  # symbol -> {"data": ..., "ts": float}


def _get_equity_symbols() -> list[dict]:
    """Get enabled US stock symbols from instruments.yaml."""
    settings = get_settings()
    instruments = settings.instruments
    symbols = []
    for item in instruments.get("us_stocks", []):
        if item.get("enabled", True):
            symbols.append({
                "symbol": item.get("yfinance") or item.get("symbol", ""),
                "name": item.get("name", ""),
            })
    return symbols


def _is_equity(symbol: str) -> bool:
    """Check if symbol is a known equity."""
    settings = get_settings()
    instruments = settings.instruments
    for item in instruments.get("us_stocks", []):
        yf_sym = item.get("yfinance") or item.get("symbol", "")
        if yf_sym.upper() == symbol.upper():
            return True
    # Also allow arbitrary tickers (yfinance will fail if no options)
    return True


@router.get("/symbols")
def get_options_symbols():
    """List equity symbols eligible for options analysis."""
    return _get_equity_symbols()


@router.get("/flow/{symbol}")
def get_options_flow(symbol: str):
    """Full options flow analysis + daily breakdown + arc reading."""
    sym = symbol.upper()

    # Check cache
    now = time.time()
    cached = _flow_cache.get(sym)
    if cached and (now - cached["ts"]) < _CACHE_TTL:
        return cached["data"]

    # Fetch chain data
    from src.fetchers.options_fetcher import OptionsFetcher

    fetcher = OptionsFetcher()
    chain_data = fetcher.get_option_chain(sym)

    if chain_data is None:
        raise HTTPException(404, f"No options data available for {sym}. The symbol may not have listed options.")

    # Run analysis
    from src.analysis.options_flow import (
        analyze_options_flow,
        build_daily_breakdown,
        generate_arc_reading,
        load_flow_history,
        save_flow_snapshot,
        _compute_arc_status,
    )

    flow = analyze_options_flow(chain_data)

    # Save snapshot for daily history
    save_flow_snapshot(sym, flow)

    # Load history and build breakdown
    history = load_flow_history(sym, days=5)
    daily_breakdown = build_daily_breakdown(history)
    arc_status = _compute_arc_status(history)

    # LLM arc reading (best-effort)
    arc_reading = None
    try:
        arc_reading = generate_arc_reading(flow, history)
    except Exception:
        pass

    response = {
        **flow,
        "daily_breakdown": daily_breakdown,
        "arc_status": arc_status,
        "arc_reading": arc_reading,
    }

    _flow_cache[sym] = {"data": response, "ts": now}
    return response


@router.get("/flow/{symbol}/enhanced")
def get_options_flow_enhanced(symbol: str):
    """Enhanced options flow with per-section LLM analysis and news."""
    sym = symbol.upper()

    # Get base flow data (reuses cache)
    base = get_options_flow(sym)

    # Fetch news headlines
    news_headlines: list[dict] = []
    try:
        from src.fetchers.newsapi_fetcher import NewsAPIFetcher
        fetcher = NewsAPIFetcher()
        raw = fetcher.get_market_headlines(query=sym, count=5)
        news_headlines = [
            {
                "title": n.get("title", ""),
                "description": n.get("description", ""),
                "url": n.get("url"),
                "source": n.get("source", {}).get("name") if isinstance(n.get("source"), dict) else n.get("source"),
                "published_at": n.get("publishedAt") or n.get("published_at"),
            }
            for n in raw
        ]
    except Exception:
        pass

    # Generate per-section LLM analyses
    section_analyses = {
        "flow_summary": None,
        "premium_analysis": None,
        "greeks_analysis": None,
        "expiry_analysis": None,
        "strike_analysis": None,
        "news_correlation": None,
        "action_items": None,
    }
    try:
        from src.analysis.options_flow import generate_section_analyses, load_flow_history
        history = load_flow_history(sym, days=5)
        section_analyses = generate_section_analyses(base, history, news_headlines)
    except Exception:
        pass

    return {
        **base,
        "news_headlines": news_headlines,
        "section_analyses": section_analyses,
    }


@router.get("/flow/{symbol}/summary")
def get_options_flow_summary(symbol: str):
    """Lightweight summary for embedding in scorecard."""
    sym = symbol.upper()

    # Try cache first
    now = time.time()
    cached = _flow_cache.get(sym)
    if cached and (now - cached["ts"]) < _CACHE_TTL:
        full = cached["data"]
        return {
            "symbol": full["symbol"],
            "conviction": full["conviction"],
            "conviction_score": full["conviction_score"],
            "cp_ratio": full["cp_ratio"],
            "total_premium": full["total_premium"],
            "top_call_strike": full.get("top_call_strike"),
            "top_put_strike": full.get("top_put_strike"),
        }

    from src.fetchers.options_fetcher import OptionsFetcher

    fetcher = OptionsFetcher()
    chain_data = fetcher.get_option_chain(sym, max_expirations=3)

    if chain_data is None:
        raise HTTPException(404, f"No options data available for {sym}")

    from src.analysis.options_flow import analyze_options_flow

    flow = analyze_options_flow(chain_data)

    return {
        "symbol": flow["symbol"],
        "conviction": flow["conviction"],
        "conviction_score": flow["conviction_score"],
        "cp_ratio": flow["cp_ratio"],
        "total_premium": flow["total_premium"],
        "top_call_strike": flow.get("top_call_strike"),
        "top_put_strike": flow.get("top_put_strike"),
    }
