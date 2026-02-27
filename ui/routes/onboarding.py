"""Onboarding wizard endpoints."""

import asyncio

from fastapi import APIRouter, HTTPException

from config.settings import get_settings, reload_settings, update_env_var
from ui.models import ApiKeyUpdate

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

# Map of UI key names to .env variable names
_KEY_MAP = {
    "telegram_bot_token": "TELEGRAM_BOT_TOKEN",
    "telegram_chat_id": "TELEGRAM_CHAT_ID",
    "twelvedata": "TWELVEDATA_API_KEY",
    "finnhub": "FINNHUB_API_KEY",
    "fred": "FRED_API_KEY",
    "newsapi": "NEWSAPI_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


@router.get("/status")
def onboarding_status():
    """Check which setup steps are complete."""
    settings = get_settings()
    return {
        "telegram_configured": bool(settings.telegram.bot_token and settings.telegram.chat_id),
        "data_apis_configured": bool(
            settings.api_keys.twelvedata or settings.api_keys.finnhub
            or settings.api_keys.fred or settings.api_keys.newsapi
        ),
        "llm_configured": settings.has_llm_key(),
    }


@router.post("/api-key")
def set_api_key(update: ApiKeyUpdate):
    """Set an API key in .env."""
    env_key = _KEY_MAP.get(update.key)
    if not env_key:
        raise HTTPException(status_code=400, detail=f"Unknown key: {update.key}")
    update_env_var(env_key, update.value)
    reload_settings()
    return {"success": True, "key": update.key}


@router.post("/test/{api_name}")
def test_api(api_name: str):
    """Test an individual API connection."""
    settings = reload_settings()

    if api_name == "yfinance":
        try:
            from src.fetchers.yfinance_fetcher import YFinanceFetcher
            fetcher = YFinanceFetcher()
            data = fetcher.get_current_price("^GSPC")
            if data:
                return {"success": True, "message": f"S&P 500: ${data['price']:,.2f}"}
            return {"success": False, "message": "No data returned"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    elif api_name == "twelvedata":
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

    elif api_name == "finnhub":
        if not settings.api_keys.finnhub:
            return {"success": False, "message": "No API key configured"}
        try:
            from src.fetchers.finnhub_fetcher import FinnhubFetcher
            fetcher = FinnhubFetcher()
            events = fetcher.get_economic_calendar()
            return {"success": True, "message": f"OK — {len(events)} upcoming events"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    elif api_name == "fred":
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

    elif api_name == "newsapi":
        if not settings.api_keys.newsapi:
            return {"success": False, "message": "No API key configured"}
        try:
            from src.fetchers.newsapi_fetcher import NewsAPIFetcher
            fetcher = NewsAPIFetcher()
            headlines = fetcher.get_top_business_headlines(count=3)
            return {"success": True, "message": f"OK — {len(headlines)} headlines"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    elif api_name == "feargreed":
        try:
            from src.fetchers.feargreed_fetcher import FearGreedFetcher
            fetcher = FearGreedFetcher()
            data = fetcher.get_fear_greed_index()
            if data:
                return {"success": True, "message": f"Score: {data['score']} — {data['classification']}"}
            return {"success": False, "message": "No data returned"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    elif api_name == "anthropic":
        if not settings.llm_keys.anthropic:
            return {"success": False, "message": "No API key configured"}
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.llm_keys.anthropic)
            client.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=10,
                messages=[{"role": "user", "content": "Say OK"}]
            )
            return {"success": True, "message": "Connected to Anthropic"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    elif api_name == "openai":
        if not settings.llm_keys.openai:
            return {"success": False, "message": "No API key configured"}
        try:
            import openai
            client = openai.OpenAI(api_key=settings.llm_keys.openai)
            client.chat.completions.create(
                model="gpt-4o-mini", max_tokens=10,
                messages=[{"role": "user", "content": "Say OK"}]
            )
            return {"success": True, "message": "Connected to OpenAI"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    elif api_name == "gemini":
        if not settings.llm_keys.gemini:
            return {"success": False, "message": "No API key configured"}
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.llm_keys.gemini)
            model = genai.GenerativeModel("gemini-2.0-flash")
            model.generate_content("Say OK")
            return {"success": True, "message": "Connected to Gemini"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    raise HTTPException(status_code=404, detail=f"Unknown API: {api_name}")


@router.post("/test-telegram")
def test_telegram():
    """Send a test Telegram message."""
    try:
        from src.delivery.telegram_bot import TelegramDelivery
        delivery = TelegramDelivery()
        success = asyncio.run(delivery.send_test_message())
        if success:
            return {"success": True, "message": "Test message sent!"}
        return {"success": False, "message": "Failed to send test message"}
    except Exception as e:
        return {"success": False, "message": str(e)}
