"""Options flow API endpoints."""

import time

from fastapi import APIRouter, HTTPException

from config.settings import get_settings
from src.utils.logging_config import get_logger

logger = get_logger("options_routes")

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
        _compute_arc_status,
        analyze_options_flow,
        build_daily_breakdown,
        generate_arc_reading,
        load_flow_history,
        save_flow_snapshot,
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


# ── V3 Endpoints ──────────────────────────────────────────────


_v2_cache: dict[str, dict] = {}  # symbol -> {"data": ..., "ts": float}
_V2_CACHE_TTL = 300


@router.get("/providers")
def get_options_providers():
    """Return which premium data providers are configured."""
    from src.fetchers.options_provider import OptionsDataProvider
    provider = OptionsDataProvider()
    return provider.get_provider_status()


@router.get("/flow/{symbol}/v2")
def get_options_flow_v2(symbol: str):
    """Full enriched options data — chain + UW flow + AV historical + advanced analysis."""
    sym = symbol.upper()

    now = time.time()
    cached = _v2_cache.get(sym)
    if cached and (now - cached["ts"]) < _V2_CACHE_TTL:
        return cached["data"]

    from src.analysis.options_advanced import (
        analyze_iv,
        classify_flow,
        compute_advanced_greeks,
        compute_conviction_v2,
        compute_flow_momentum,
        correlate_dark_pool,
        detect_unusual_activity,
    )
    from src.analysis.options_flow import (
        _compute_arc_status,
        analyze_options_flow,
        build_daily_breakdown,
        generate_arc_reading,
        load_flow_history,
        save_flow_snapshot,
    )
    from src.fetchers.options_provider import OptionsDataProvider

    provider = OptionsDataProvider()
    enriched = provider.get_enriched_data(sym)

    if "error" in enriched:
        raise HTTPException(404, enriched["error"])

    chain_data = enriched["chain_data"]

    # Base flow analysis (same as V1)
    flow = analyze_options_flow(chain_data)
    save_flow_snapshot(sym, flow)
    history = load_flow_history(sym, days=5)
    daily_breakdown = build_daily_breakdown(history)
    arc_status = _compute_arc_status(history)

    arc_reading = None
    try:
        arc_reading = generate_arc_reading(flow, history)
    except Exception:
        pass

    # Advanced analysis
    flow_alerts = enriched.get("flow_alerts")
    dark_pool = enriched.get("dark_pool")
    institutional = enriched.get("institutional")
    historical_iv = enriched.get("historical_iv")
    flow_intervals = enriched.get("flow_intervals")

    unusual = detect_unusual_activity(flow_alerts, chain_data)
    smart_money = classify_flow(flow_alerts)
    conviction_v2 = compute_conviction_v2(
        flow, flow_alerts, dark_pool, institutional, historical_iv, chain_data
    )
    iv_analysis = analyze_iv(chain_data, historical_iv, flow.get("stock_price", 0))
    advanced_greeks = compute_advanced_greeks(chain_data, flow.get("stock_price", 0))
    dp_correlation = correlate_dark_pool(dark_pool, flow_alerts, flow.get("stock_price", 0))
    momentum = compute_flow_momentum(flow, flow_alerts)

    # Fetch news
    news_headlines: list[dict] = []
    try:
        from src.fetchers.newsapi_fetcher import NewsAPIFetcher
        nf = NewsAPIFetcher()
        raw = nf.get_market_headlines(query=sym, count=5)
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

    # LLM section analyses (best-effort)
    section_analyses = {
        "flow_summary": None,
        "premium_analysis": None,
        "greeks_analysis": None,
        "expiry_analysis": None,
        "strike_analysis": None,
        "news_correlation": None,
        "action_items": None,
        "sweep_analysis": None,
        "smart_money_analysis": None,
        "gex_analysis": None,
        "dark_pool_analysis": None,
        "iv_analysis": None,
    }
    try:
        from src.analysis.options_flow import generate_section_analyses
        base_analyses = generate_section_analyses(
            {**flow, "daily_breakdown": daily_breakdown, "arc_status": arc_status},
            history,
            news_headlines,
        )
        section_analyses.update(base_analyses)
    except Exception:
        pass

    # Generate V3-specific LLM analyses
    try:
        from src.analysis.llm_providers import LLMProvider
        llm = LLMProvider()
        _gen_v3_analyses(llm, section_analyses, sym, flow, unusual, smart_money, advanced_greeks, dp_correlation, iv_analysis)
    except Exception:
        pass

    response = {
        **flow,
        "daily_breakdown": daily_breakdown,
        "arc_status": arc_status,
        "arc_reading": arc_reading,
        "news_headlines": news_headlines,
        "section_analyses": section_analyses,
        # V3 additions
        "flow_alerts": flow_alerts,
        "dark_pool": dark_pool,
        "institutional": institutional,
        "flow_intervals": flow_intervals,
        "historical_iv": historical_iv,
        "unusual_activity": unusual,
        "smart_money": smart_money,
        "conviction_v2": conviction_v2,
        "iv_analysis": iv_analysis,
        "advanced_greeks": advanced_greeks,
        "dp_correlation": dp_correlation,
        "flow_momentum": momentum,
        "provider_status": enriched.get("provider_status", {}),
    }

    _v2_cache[sym] = {"data": response, "ts": now}
    return response


@router.get("/flow/{symbol}/alerts")
def get_flow_alerts(symbol: str):
    """Lightweight sweep alert polling (for 30s refresh)."""
    sym = symbol.upper()
    from src.fetchers.options_provider import OptionsDataProvider
    provider = OptionsDataProvider()
    alerts = provider.get_flow_alerts_only(sym)
    return {"symbol": sym, "alerts": alerts, "count": len(alerts)}


def _gen_v3_analyses(
    llm, section_analyses: dict, symbol: str, flow: dict,
    unusual: dict, smart_money: dict, advanced_greeks: dict | None,
    dp_correlation: dict | None, iv_analysis: dict | None,
):
    """Generate V3-specific LLM analyses for sweep, smart money, GEX, dark pool, IV."""
    system = (
        "You are an options flow analyst writing for traders. Explain clearly what the data means "
        "and why it matters. Write in direct prose. No emojis, no markdown, no bullet points."
    )

    # Load prompts
    try:
        from pathlib import Path

        import yaml as _yaml
        prompts_path = Path(__file__).parent.parent.parent / "config" / "prompts.yaml"
        if prompts_path.exists():
            with open(prompts_path) as f:
                sections_config = (_yaml.safe_load(f) or {}).get("sections", {})
        else:
            sections_config = {}
    except Exception:
        sections_config = {}

    base = f"Symbol: {symbol}\nStock Price: ${flow.get('stock_price')}\n"

    # Sweep analysis
    if unusual.get("available"):
        prompt = sections_config.get("options_sweep_analysis", {}).get("prompt",
            "Interpret the unusual sweep/block activity. What do the sweep counts, dominant side, "
            "and golden sweeps tell us about institutional conviction? 2-3 sentences.")
        ctx = (
            base
            + f"Sweep Count: {unusual.get('sweep_count')}\n"
            + f"Block Count: {unusual.get('block_count')}\n"
            + f"Golden Sweeps: {unusual.get('golden_sweep_count')}\n"
            + f"Total Sweep Premium: ${unusual.get('total_sweep_premium', 0):,.0f}\n"
            + f"Dominant Side: {unusual.get('dominant_side')}\n"
        )
        try:
            r = llm.generate(system, ctx + "\n" + prompt, max_tokens=300)
            section_analyses["sweep_analysis"] = r.text if r else None
        except Exception:
            pass

    # Smart money analysis
    if smart_money.get("available"):
        prompt = sections_config.get("options_smart_money", {}).get("prompt",
            "Analyze the smart money vs retail divergence. What does the split tell us about "
            "informed vs uninformed positioning? Is there a divergence signal? 2-3 sentences.")
        ctx = (
            base
            + f"Smart Money: {smart_money.get('smart_money_pct')}% ({smart_money.get('smart_money_sentiment')})\n"
            + f"Retail: {smart_money.get('retail_pct')}% ({smart_money.get('retail_sentiment')})\n"
            + f"Divergence Score: {smart_money.get('divergence_score')}/100\n"
        )
        try:
            r = llm.generate(system, ctx + "\n" + prompt, max_tokens=300)
            section_analyses["smart_money_analysis"] = r.text if r else None
        except Exception:
            pass

    # GEX analysis
    if advanced_greeks:
        prompt = sections_config.get("options_gex_analysis", {}).get("prompt",
            "Explain the gamma exposure implications for price action. Is the market in a positive "
            "or negative GEX regime? Where is the GEX flip level and what does it mean? 2-3 sentences.")
        ctx = (
            base
            + f"Total GEX: {advanced_greeks.get('total_gex', 0):,.0f}\n"
            + f"Total DEX: {advanced_greeks.get('total_dex', 0):,.0f}\n"
            + f"GEX Flip Level: ${advanced_greeks.get('gex_flip_level')}\n"
            + f"GEX Regime: {advanced_greeks.get('gex_regime')} — {advanced_greeks.get('gex_description')}\n"
        )
        try:
            r = llm.generate(system, ctx + "\n" + prompt, max_tokens=300)
            section_analyses["gex_analysis"] = r.text if r else None
        except Exception:
            pass

    # Dark pool analysis
    if dp_correlation:
        prompt = sections_config.get("options_dark_pool_analysis", {}).get("prompt",
            "Analyze the dark pool prints and their correlation with options flow. What does the "
            "dark pool price vs spot spread and volume tell us? 2-3 sentences.")
        ctx = (
            base
            + f"Total DP Prints: {dp_correlation.get('total_prints')}\n"
            + f"Total Notional: ${dp_correlation.get('total_notional', 0):,.0f}\n"
            + f"Above Spot: {dp_correlation.get('above_spot')}\n"
            + f"Below Spot: {dp_correlation.get('below_spot')}\n"
            + f"DP Sentiment: {dp_correlation.get('dp_sentiment')}\n"
            + f"Avg DP Price vs Spot: {dp_correlation.get('price_vs_spot_pct')}%\n"
        )
        try:
            r = llm.generate(system, ctx + "\n" + prompt, max_tokens=300)
            section_analyses["dark_pool_analysis"] = r.text if r else None
        except Exception:
            pass

    # IV analysis
    if iv_analysis:
        prompt = sections_config.get("options_iv_analysis", {}).get("prompt",
            "Analyze the implied volatility data. What does the IV percentile, skew, and term structure "
            "tell us about market expectations? Is there crush risk? 2-3 sentences.")
        ctx = (
            base
            + f"Current IV: {iv_analysis.get('current_iv')}\n"
            + f"IV Percentile: {iv_analysis.get('iv_percentile')}\n"
            + f"IV Skew (put - call): {iv_analysis.get('iv_skew')}\n"
            + f"Term Structure: {iv_analysis.get('term_structure')}\n"
            + f"Near-Term IV: {iv_analysis.get('near_term_iv')}\n"
            + f"Far-Term IV: {iv_analysis.get('far_term_iv')}\n"
            + f"Crush Risk: {iv_analysis.get('crush_risk')}\n"
        )
        try:
            r = llm.generate(system, ctx + "\n" + prompt, max_tokens=300)
            section_analyses["iv_analysis"] = r.text if r else None
        except Exception:
            pass
