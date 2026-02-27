"""Data source health and management endpoints."""

import re

from fastapi import APIRouter, HTTPException

from config.settings import (
    get_custom_source_by_id,
    get_settings,
    load_custom_sources,
    reload_settings,
    save_custom_sources,
    update_env_var,
)
from ui.models import ApiKeyUpdate, CustomSourceCreate, CustomSourceUpdate, SourceToggle

router = APIRouter(prefix="/api/sources", tags=["sources"])

_SOURCES = {
    "yfinance": {
        "name": "yFinance",
        "needs_key": False,
        "env_key": None,
        "description": "Primary data source for stocks, indices, forex, crypto. No API key required.",
    },
    "twelvedata": {
        "name": "Twelve Data",
        "needs_key": True,
        "env_key": "TWELVEDATA_API_KEY",
        "description": "Real-time forex quotes and technical indicators. 800 calls/day free tier.",
    },
    "finnhub": {
        "name": "Finnhub",
        "needs_key": True,
        "env_key": "FINNHUB_API_KEY",
        "description": "Economic calendar and market news. 60 calls/min free tier.",
    },
    "fred": {
        "name": "FRED",
        "needs_key": True,
        "env_key": "FRED_API_KEY",
        "description": "Federal Reserve economic data (CPI, GDP, payrolls, rates). Free, unlimited.",
    },
    "newsapi": {
        "name": "NewsAPI",
        "needs_key": True,
        "env_key": "NEWSAPI_KEY",
        "description": "Market headlines for sentiment analysis. 100 calls/day free tier.",
    },
    "feargreed": {
        "name": "Fear & Greed Index",
        "needs_key": False,
        "env_key": None,
        "description": "CNN Fear & Greed Index. No API key required.",
    },
}


@router.get("")
def list_sources():
    """Get all data sources with their status."""
    settings = get_settings()
    result = []

    for key, info in _SOURCES.items():
        configured = True
        if info["needs_key"]:
            env_key = info["env_key"]
            if env_key == "TWELVEDATA_API_KEY":
                configured = bool(settings.api_keys.twelvedata)
            elif env_key == "FINNHUB_API_KEY":
                configured = bool(settings.api_keys.finnhub)
            elif env_key == "FRED_API_KEY":
                configured = bool(settings.api_keys.fred)
            elif env_key == "NEWSAPI_KEY":
                configured = bool(settings.api_keys.newsapi)

        result.append({
            "id": key,
            "name": info["name"],
            "needs_key": info["needs_key"],
            "configured": configured,
            "description": info["description"],
        })

    return result


@router.post("/{name}/test")
def test_source(name: str):
    """Test a data source connection."""
    if name not in _SOURCES:
        raise HTTPException(status_code=404, detail=f"Unknown source: {name}")

    settings = reload_settings()

    if name == "yfinance":
        try:
            from src.fetchers.yfinance_fetcher import YFinanceFetcher
            fetcher = YFinanceFetcher()
            data = fetcher.get_current_price("^GSPC")
            if data:
                return {"success": True, "message": f"S&P 500: ${data['price']:,.2f}"}
            return {"success": False, "message": "No data returned"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    elif name == "twelvedata":
        if not settings.api_keys.twelvedata:
            return {"success": False, "message": "No API key configured"}
        try:
            from src.fetchers.twelvedata_fetcher import TwelveDataFetcher
            fetcher = TwelveDataFetcher()
            data = fetcher.get_forex_quote("EUR/USD")
            if data:
                return {"success": True, "message": f"EUR/USD: {data['price']:.5f}"}
            return {"success": False, "message": "No data returned"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    elif name == "finnhub":
        if not settings.api_keys.finnhub:
            return {"success": False, "message": "No API key configured"}
        try:
            from src.fetchers.finnhub_fetcher import FinnhubFetcher
            fetcher = FinnhubFetcher()
            events = fetcher.get_economic_calendar()
            return {"success": True, "message": f"OK — {len(events)} upcoming events"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    elif name == "fred":
        if not settings.api_keys.fred:
            return {"success": False, "message": "No API key configured"}
        try:
            from src.fetchers.fred_fetcher import FREDFetcher
            fetcher = FREDFetcher()
            data = fetcher.get_series_latest("DGS10")
            if data:
                return {"success": True, "message": f"10Y: {data['value']:.2f}%"}
            return {"success": False, "message": "No data returned"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    elif name == "newsapi":
        if not settings.api_keys.newsapi:
            return {"success": False, "message": "No API key configured"}
        try:
            from src.fetchers.newsapi_fetcher import NewsAPIFetcher
            fetcher = NewsAPIFetcher()
            headlines = fetcher.get_top_business_headlines(count=3)
            return {"success": True, "message": f"OK — {len(headlines)} headlines"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    elif name == "feargreed":
        try:
            from src.fetchers.feargreed_fetcher import FearGreedFetcher
            fetcher = FearGreedFetcher()
            data = fetcher.get_fear_greed_index()
            if data:
                return {"success": True, "message": f"Score: {data['score']} — {data['classification']}"}
            return {"success": False, "message": "No data returned"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    return {"success": False, "message": "Unknown source"}


@router.put("/{name}/api-key")
def update_source_key(name: str, body: ApiKeyUpdate):
    """Update a data source's API key."""
    if name not in _SOURCES:
        raise HTTPException(status_code=404, detail=f"Unknown source: {name}")

    source = _SOURCES[name]
    if not source["needs_key"]:
        raise HTTPException(status_code=400, detail=f"{name} does not require an API key")

    update_env_var(source["env_key"], body.value)
    reload_settings()
    return {"success": True}


# ── Custom Data Sources CRUD ─────────────────────────────────


def _slugify(name: str) -> str:
    """Generate a URL-safe id from a source name."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "custom"


@router.get("/custom")
def list_custom_sources():
    """List all custom data sources."""
    return load_custom_sources()


@router.post("/custom")
def create_custom_source(body: CustomSourceCreate):
    """Create a new custom data source."""
    sources = load_custom_sources()
    source_id = _slugify(body.name)

    # Ensure unique id
    existing_ids = {s["id"] for s in sources}
    base_id = source_id
    counter = 1
    while source_id in existing_ids:
        source_id = f"{base_id}_{counter}"
        counter += 1

    new_source = {"id": source_id, **body.model_dump(exclude_none=True)}
    # Serialize nested models to dicts
    if body.auth:
        new_source["auth"] = body.auth.model_dump(exclude_none=True)
    if body.digest_integration:
        new_source["digest_integration"] = body.digest_integration.model_dump(exclude_none=True)

    sources.append(new_source)
    save_custom_sources(sources)
    return new_source


@router.get("/custom/{source_id}")
def get_custom_source(source_id: str):
    """Get a single custom data source."""
    source = get_custom_source_by_id(source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Custom source '{source_id}' not found")
    return source


@router.put("/custom/{source_id}")
def update_custom_source(source_id: str, body: CustomSourceUpdate):
    """Update (partial) a custom data source."""
    sources = load_custom_sources()
    idx = next((i for i, s in enumerate(sources) if s["id"] == source_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail=f"Custom source '{source_id}' not found")

    updates = body.model_dump(exclude_none=True)
    # Serialize nested models
    if body.auth is not None:
        updates["auth"] = body.auth.model_dump(exclude_none=True)
    if body.digest_integration is not None:
        updates["digest_integration"] = body.digest_integration.model_dump(exclude_none=True)

    sources[idx].update(updates)
    save_custom_sources(sources)
    return sources[idx]


@router.delete("/custom/{source_id}")
def delete_custom_source(source_id: str):
    """Delete a custom data source."""
    sources = load_custom_sources()
    new_sources = [s for s in sources if s["id"] != source_id]
    if len(new_sources) == len(sources):
        raise HTTPException(status_code=404, detail=f"Custom source '{source_id}' not found")
    save_custom_sources(new_sources)
    return {"success": True}


@router.post("/custom/{source_id}/test")
def test_custom_source(source_id: str):
    """Test a custom data source connection."""
    source = get_custom_source_by_id(source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Custom source '{source_id}' not found")

    from src.fetchers.custom_fetcher import CustomSourceFetcher
    fetcher = CustomSourceFetcher(source)
    return fetcher.test_connection()


@router.put("/custom/{source_id}/toggle")
def toggle_custom_source(source_id: str, body: SourceToggle):
    """Enable or disable a custom data source."""
    sources = load_custom_sources()
    idx = next((i for i, s in enumerate(sources) if s["id"] == source_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail=f"Custom source '{source_id}' not found")

    sources[idx]["enabled"] = body.enabled
    save_custom_sources(sources)
    return sources[idx]
