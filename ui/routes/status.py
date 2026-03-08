"""Dashboard status endpoint."""

import json

from fastapi import APIRouter

from config.settings import PROJECT_ROOT, get_settings

router = APIRouter(prefix="/api", tags=["status"])

HISTORY_FILE = PROJECT_ROOT / "logs" / "digest_history.json"
OPTIONS_FLOW_DIR = PROJECT_ROOT / "logs" / "options_flow"


@router.get("/status")
def get_status():
    """Dashboard health: API configs, cache stats, onboarding status, market snapshot, options conviction, retrace."""
    settings = get_settings()

    apis = {
        "telegram": {
            "configured": bool(settings.telegram.bot_token and settings.telegram.chat_id),
            "name": "Telegram",
        },
        "yfinance": {
            "configured": True,
            "name": "yFinance (no key needed)",
        },
        "twelvedata": {
            "configured": bool(settings.api_keys.twelvedata),
            "name": "Twelve Data",
        },
        "finnhub": {
            "configured": bool(settings.api_keys.finnhub),
            "name": "Finnhub",
        },
        "fred": {
            "configured": bool(settings.api_keys.fred),
            "name": "FRED",
        },
        "newsapi": {
            "configured": bool(settings.api_keys.newsapi),
            "name": "NewsAPI",
        },
        "feargreed": {
            "configured": True,
            "name": "Fear & Greed (no key needed)",
        },
        "anthropic": {
            "configured": bool(settings.llm_keys.anthropic),
            "name": "Anthropic (Claude)",
        },
        "openai": {
            "configured": bool(settings.llm_keys.openai),
            "name": "OpenAI",
        },
        "gemini": {
            "configured": bool(settings.llm_keys.gemini),
            "name": "Google Gemini",
        },
        "unusual_whales": {
            "configured": bool(settings.api_keys.unusual_whales),
            "name": "Unusual Whales",
        },
        "alpha_vantage": {
            "configured": bool(settings.api_keys.alpha_vantage),
            "name": "Alpha Vantage",
        },
    }

    # Cache stats
    cache_dir = settings.cache_dir
    cache_files = list(cache_dir.glob("*.json")) if cache_dir.exists() else []
    cache_size = sum(f.stat().st_size for f in cache_files)

    # Recent history
    recent_history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text())
            recent_history = history[-10:]
        except (json.JSONDecodeError, OSError):
            pass

    # Onboarding: check minimum config
    required_configured = bool(
        settings.telegram.bot_token
        and settings.telegram.chat_id
    )

    # Market snapshot (SPY, QQQ, VIX)
    market_snapshot = _get_market_snapshot()

    # Options conviction summary (from recent snapshots)
    options_conviction = _get_options_conviction()

    # Retrace performance summary
    retrace_summary = _get_retrace_summary()

    return {
        "apis": apis,
        "cache": {
            "file_count": len(cache_files),
            "total_size_bytes": cache_size,
        },
        "recent_history": recent_history,
        "onboarding_complete": required_configured,
        "timezone": settings.timezone,
        "log_level": settings.log_level,
        "has_llm_key": settings.has_llm_key(),
        "market_snapshot": market_snapshot,
        "options_conviction": options_conviction,
        "retrace_summary": retrace_summary,
    }


def _get_market_snapshot() -> dict | None:
    """Fetch latest prices for SPY, QQQ, VIX."""
    try:
        from src.fetchers.yfinance_fetcher import YFinanceFetcher
        yf = YFinanceFetcher()
        batch = yf.get_batch_prices(["SPY", "QQQ", "^VIX"])

        result = {}
        mapping = {"SPY": "spy", "QQQ": "qqq", "^VIX": "vix"}
        for yf_sym, key in mapping.items():
            data = batch.get(yf_sym)
            if data:
                result[key] = {
                    "price": data.get("price"),
                    "change_pct": data.get("change_pct"),
                }

        if result:
            from datetime import datetime, timezone
            result["fetched_at"] = datetime.now(timezone.utc).isoformat()
            return result
    except Exception:
        pass
    return None


def _get_options_conviction() -> list[dict]:
    """Read today's options flow snapshots for conviction summary."""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")

    results = []
    try:
        if not OPTIONS_FLOW_DIR.exists():
            return []

        for sym_dir in OPTIONS_FLOW_DIR.iterdir():
            if not sym_dir.is_dir():
                continue
            snapshot_file = sym_dir / f"{today}.json"
            if not snapshot_file.exists():
                continue
            try:
                data = json.loads(snapshot_file.read_text())
                results.append({
                    "symbol": data.get("symbol", sym_dir.name),
                    "conviction": data.get("conviction", "?"),
                    "conviction_score": data.get("conviction_score", 0),
                    "cp_ratio": data.get("cp_ratio", 0),
                    "stock_price": data.get("stock_price", 0),
                })
            except (json.JSONDecodeError, OSError):
                continue

        # Sort by conviction score desc, top 5
        results.sort(key=lambda x: x.get("conviction_score", 0), reverse=True)
        return results[:5]
    except Exception:
        return []


def _get_retrace_summary() -> dict | None:
    """Get aggregate retrace performance summary."""
    try:
        from src.retrace.grader import aggregate_performance
        from src.retrace.snapshot import list_snapshots, load_snapshot

        snapshots_meta = list_snapshots(limit=30)
        if not snapshots_meta:
            return None

        snapshots = []
        for meta in snapshots_meta:
            s = load_snapshot(meta["date"])
            if s:
                snapshots.append(s)

        if not snapshots:
            return None

        perf = aggregate_performance(snapshots)
        if not perf:
            return None

        return {
            "total_graded": perf.get("total_graded", 0),
            "win_rate": perf.get("win_rate", 0),
            "avg_r": perf.get("avg_r"),
            "days_tracked": len(snapshots),
        }
    except Exception:
        return None
