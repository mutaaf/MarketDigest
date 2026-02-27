"""Settings endpoints — read/write .env, export/import config."""

import asyncio
import io
import zipfile

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from config.settings import PROJECT_ROOT, add_chat_id, get_settings, reload_settings, remove_chat_id, update_env_var
from ui.models import RecipientAdd, SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])

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
