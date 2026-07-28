"""Signal API routes — scan, history, backtest."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/signals", tags=["signals"])


class BacktestRequest(BaseModel):
    symbol: str = "JPY=X"
    asset_type: str = "forex"
    lookback_months: int = 6
    start_balance: float = 500.0


@router.get("/scan")
async def scan_signals():
    """Run a signal scan across all configured instruments."""
    from src.signals.engine import scan_signals as _scan
    try:
        signals = _scan()
        return {
            "count": len(signals),
            "signals": [s.to_dict() for s in signals],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest():
    """Get the most recent scan results."""
    from src.signals.engine import get_latest_signals
    return {"signals": get_latest_signals()}


@router.get("/history")
async def get_history(days: int = 7):
    """Get signal history for the past N days."""
    from src.signals.engine import load_signal_history
    signals = load_signal_history(days=days)
    return {"count": len(signals), "signals": signals}


@router.post("/backtest")
async def run_backtest(req: BacktestRequest):
    """Run a backtest on a strategy."""
    from src.signals.engine import backtest_strategy
    try:
        result = backtest_strategy(
            yf_ticker=req.symbol,
            asset_type=req.asset_type,
            lookback_months=req.lookback_months,
            start_balance=req.start_balance,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_signal(signal_data: dict, force: bool = False):
    """Get AI-powered explanation with news, sentiment, and economic context.
    Results are cached to disk with TTL. Pass force=true to regenerate.
    """
    signal_id = signal_data.get("id", "")

    from src.signals.ai_cache import generate_and_cache_insight, get_cached_insight

    # Check cache first (unless force refresh)
    if not force and signal_id:
        cached = get_cached_insight(signal_id)
        if cached and cached["freshness"] in ("fresh", "stale"):
            return {
                "explanation": cached["explanation"],
                "provider": "cache",
                "freshness": cached["freshness"],
                "age_label": cached["age_label"],
                "timestamp": cached["timestamp"],
            }

    # Generate new with market context
    try:
        market_context = _fetch_market_context(signal_data.get("symbol", ""))
        explanation = generate_and_cache_insight(signal_data, market_context, force=True)

        # Get freshness info for the new entry
        info = get_cached_insight(signal_id) if signal_id else None

        return {
            "explanation": explanation or "AI analysis unavailable — check that API keys are configured in Settings.",
            "provider": "ai",
            "freshness": info["freshness"] if info else "fresh",
            "age_label": info["age_label"] if info else "just now",
            "timestamp": info["timestamp"] if info else "",
            "context": market_context,
        }
    except Exception as e:
        return {
            "explanation": f"AI analysis error: {str(e)}. Check API keys in Settings.",
            "provider": "error",
            "freshness": "error",
            "age_label": "",
            "timestamp": "",
        }


@router.get("/market-context")
async def get_market_context():
    """Get current market context — news, sentiment, events."""
    return _fetch_market_context("")


def _fetch_market_context(symbol: str = "") -> dict:
    """Fetch news, sentiment, economic events for signal context."""
    context = {
        "news": [],
        "sentiment": {},
        "economic_events": [],
        "earnings": [],
        "fear_greed": {},
    }

    # Fear & Greed
    try:
        from src.fetchers.feargreed_fetcher import FearGreedFetcher
        fg = FearGreedFetcher()
        fg_data = fg.get_fear_greed_index()
        if fg_data:
            context["fear_greed"] = fg_data
    except Exception:
        pass

    # News headlines
    try:
        from src.fetchers.finnhub_fetcher import FinnhubFetcher
        finnhub = FinnhubFetcher()
        news = finnhub.get_market_news(category="general", count=10)
        if news:
            context["news"] = [
                {"headline": n.get("headline", ""), "source": n.get("source", ""),
                 "summary": n.get("summary", "")[:200]}
                for n in news[:8]
            ]
    except Exception:
        pass

    # Try NewsAPI as fallback
    if not context["news"]:
        try:
            from src.fetchers.newsapi_fetcher import NewsAPIFetcher
            newsapi = NewsAPIFetcher()
            headlines = newsapi.get_top_business_headlines(count=8)
            if headlines:
                context["news"] = [
                    {"headline": h.get("title", ""), "source": h.get("source", ""),
                     "summary": h.get("description", "")[:200]}
                    for h in headlines[:8]
                ]
        except Exception:
            pass

    # Economic events
    try:
        from src.fetchers.finnhub_fetcher import FinnhubFetcher
        finnhub = FinnhubFetcher()
        events = finnhub.get_economic_calendar(days_ahead=2)
        if events:
            # Only high/medium impact
            context["economic_events"] = [
                {"event": e.get("event", ""), "date": e.get("date", ""),
                 "impact": e.get("impact", ""), "actual": e.get("actual"),
                 "estimate": e.get("estimate"), "prev": e.get("prev")}
                for e in events if e.get("impact") in ("high", "medium")
            ][:10]
    except Exception:
        pass

    # Earnings for the symbol
    if symbol:
        try:
            from src.fetchers.finnhub_fetcher import FinnhubFetcher
            finnhub = FinnhubFetcher()
            earnings = finnhub.get_earnings_calendar(days_ahead=7)
            if earnings:
                context["earnings"] = [
                    e for e in earnings if e.get("symbol") == symbol
                ][:3]
        except Exception:
            pass

    # Composite sentiment
    try:
        from src.analysis.sentiment import compute_composite_sentiment
        sentiment = compute_composite_sentiment(
            fg_data=context.get("fear_greed"),
            headlines=context.get("news"),
        )
        if sentiment:
            context["sentiment"] = sentiment
    except Exception:
        pass

    return context


@router.post("/autopilot/start")
async def start_autopilot(interval: int = 5):
    """Start the autopilot background scanner."""
    from src.signals.autopilot import start_autopilot
    start_autopilot(interval_minutes=interval)
    return {"status": "started", "interval_minutes": interval}


@router.post("/autopilot/stop")
async def stop_autopilot():
    """Stop the autopilot background scanner."""
    from src.signals.autopilot import stop_autopilot
    stop_autopilot()
    return {"status": "stopped"}


@router.get("/autopilot/status")
async def autopilot_status():
    """Get autopilot status."""
    from src.signals.autopilot import get_autopilot_status
    return get_autopilot_status()


@router.post("/autopilot/cycle")
async def run_one_cycle():
    """Run one scan cycle manually."""
    from src.signals.autopilot import run_scan_cycle
    return run_scan_cycle()


@router.post("/autopilot/summary")
async def send_summary():
    """Send daily summary via Telegram."""
    from src.signals.autopilot import send_daily_summary
    send_daily_summary()
    return {"status": "sent"}


@router.get("/config")
async def get_signal_config():
    """Get current signal configuration."""
    from pathlib import Path

    import yaml
    config_path = Path(__file__).parent.parent.parent / "config" / "signals.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config
