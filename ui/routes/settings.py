"""Settings endpoints — read/write .env, export/import config."""

import asyncio
import io
import zipfile

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from config.settings import PROJECT_ROOT, add_chat_id, get_env_var, get_settings, reload_settings, remove_chat_id, update_env_var
from ui.models import ApiKeyUpdate, RecipientAdd, SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])

# API key definitions: (ui_key, env_var, display_name, category)
_API_KEY_DEFS = [
    ("telegram_bot_token", "TELEGRAM_BOT_TOKEN", "Telegram Bot Token", "telegram"),
    ("telegram_chat_id", "TELEGRAM_CHAT_ID", "Telegram Chat ID", "telegram"),
    ("twelvedata", "TWELVEDATA_API_KEY", "Twelve Data", "data"),
    ("finnhub", "FINNHUB_API_KEY", "Finnhub", "data"),
    ("fred", "FRED_API_KEY", "FRED", "data"),
    ("newsapi", "NEWSAPI_KEY", "NewsAPI", "data"),
    ("anthropic", "ANTHROPIC_API_KEY", "Anthropic (Claude)", "llm"),
    ("openai", "OPENAI_API_KEY", "OpenAI", "llm"),
    ("gemini", "GEMINI_API_KEY", "Google Gemini", "llm"),
    ("unusual_whales", "UNUSUAL_WHALES_API_KEY", "Unusual Whales", "options"),
    ("alpha_vantage", "ALPHA_VANTAGE_API_KEY", "Alpha Vantage", "options"),
]

CONFIG_FILES = [
    "config/instruments.yaml",
    "config/prompts.yaml",
    "config/digests.yaml",
    ".env",
]


@router.get("")
def get_current_settings():
    """Get current settings (safe values only)."""
    settings = get_settings()
    return {
        "timezone": settings.timezone,
        "log_level": settings.log_level,
    }


@router.put("")
def update_settings(update: SettingsUpdate):
    """Update timezone and/or log level."""
    if update.timezone is not None:
        update_env_var("TIMEZONE", update.timezone)
    if update.log_level is not None:
        update_env_var("LOG_LEVEL", update.log_level)
    reload_settings()
    return {"success": True}


@router.get("/export")
def export_config():
    """Export all config files as a zip."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path in CONFIG_FILES:
            full_path = PROJECT_ROOT / rel_path
            if full_path.exists():
                zf.write(full_path, rel_path)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=market-digest-config.zip"},
    )


@router.post("/import")
async def import_config(file: UploadFile = File(...)):
    """Import config from a zip file."""
    content = await file.read()
    buf = io.BytesIO(content)

    with zipfile.ZipFile(buf, "r") as zf:
        for name in zf.namelist():
            if name in CONFIG_FILES:
                target = PROJECT_ROOT / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(name))

    reload_settings()
    return {"success": True, "imported": [n for n in zipfile.ZipFile(io.BytesIO(content)).namelist() if n in CONFIG_FILES]}


# ── Telegram Recipients ──────────────────────────────────────────


@router.get("/recipients")
def get_recipients():
    """List all Telegram recipient chat IDs with labels."""
    settings = get_settings()
    return [
        {"chat_id": cid, "label": settings.telegram.chat_labels.get(cid, "")}
        for cid in settings.telegram.chat_ids
    ]


@router.post("/recipients")
def add_recipient(body: RecipientAdd):
    """Add a new Telegram recipient."""
    chat_id = body.chat_id.strip()
    if not chat_id:
        raise HTTPException(status_code=400, detail="chat_id is required")
    add_chat_id(chat_id, body.label.strip())
    return {"success": True}


@router.delete("/recipients/{chat_id}")
def delete_recipient(chat_id: str):
    """Remove a Telegram recipient."""
    remove_chat_id(chat_id)
    return {"success": True}


@router.post("/recipients/{chat_id}/test")
def test_recipient(chat_id: str):
    """Send a test message to a specific recipient."""
    try:
        from src.delivery.telegram_bot import TelegramDelivery
        delivery = TelegramDelivery()
        success = asyncio.run(delivery.send_test_message(chat_id=chat_id))
        if success:
            return {"success": True, "message": "Test message sent!"}
        return {"success": False, "message": "Failed to send test message"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── API Keys Management ──────────────────────────────────────


@router.get("/api-keys")
def get_api_keys_status():
    """Return all API keys with configured status (values masked)."""
    settings = get_settings()
    result = []
    for ui_key, env_var, label, category in _API_KEY_DEFS:
        raw = get_env_var(env_var)
        has_value = bool(raw and raw not in ("", "your_" + ui_key + "_here"))
        masked = ""
        if raw and has_value:
            masked = raw[:4] + "..." + raw[-4:] if len(raw) > 12 else "****"
        result.append({
            "key": ui_key,
            "env_var": env_var,
            "label": label,
            "category": category,
            "configured": has_value,
            "masked_value": masked,
        })
    return result


@router.post("/api-keys")
def set_api_key(update: ApiKeyUpdate):
    """Set an API key in .env and reload settings."""
    env_var = None
    for ui_key, ev, _label, _cat in _API_KEY_DEFS:
        if ui_key == update.key:
            env_var = ev
            break
    if not env_var:
        raise HTTPException(status_code=400, detail=f"Unknown key: {update.key}")
    update_env_var(env_var, update.value)
    reload_settings()
    return {"success": True, "key": update.key}


@router.delete("/api-keys/{key_name}")
def remove_api_key(key_name: str):
    """Remove an API key from .env."""
    env_var = None
    for ui_key, ev, _label, _cat in _API_KEY_DEFS:
        if ui_key == key_name:
            env_var = ev
            break
    if not env_var:
        raise HTTPException(status_code=400, detail=f"Unknown key: {key_name}")
    update_env_var(env_var, "")
    reload_settings()
    return {"success": True, "key": key_name}
