"""Digest configuration, run, and send endpoints."""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from config.settings import PROJECT_ROOT, reload_settings
from ui.models import DigestRunRequest, DigestSendRequest, DigestConfigUpdate

router = APIRouter(prefix="/api/digests", tags=["digests"])

DIGESTS_YAML = PROJECT_ROOT / "config" / "digests.yaml"
HISTORY_FILE = PROJECT_ROOT / "logs" / "digest_history.json"


def _load_digests_yaml() -> dict:
    if DIGESTS_YAML.exists():
        with open(DIGESTS_YAML) as f:
            return yaml.safe_load(f) or {}
    return {}


def _save_digests_yaml(config: dict) -> None:
    with open(DIGESTS_YAML, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


@router.get("/config")
def get_digest_config():
    """Get all digest configurations."""
    return _load_digests_yaml()


@router.put("/config/{digest_type}")
def update_digest_config(digest_type: str, body: DigestConfigUpdate):
    """Update a specific digest type's configuration."""
    if digest_type not in ("morning", "afternoon", "weekly", "daytrade"):
        raise HTTPException(status_code=400, detail=f"Invalid digest type: {digest_type}")

    config = _load_digests_yaml()
    if digest_type not in config:
        config[digest_type] = {}

    if body.sections is not None:
        config[digest_type]["sections"] = body.sections
    if body.default_mode is not None:
        config[digest_type]["default_mode"] = body.default_mode
    if body.schedule is not None:
        config[digest_type]["schedule"] = body.schedule

    _save_digests_yaml(config)
    return {"success": True}


@router.post("/run")
def run_digest(body: DigestRunRequest):
    """Run a digest and return the HTML content."""
    if body.digest_type not in ("morning", "afternoon", "weekly", "daytrade"):
        raise HTTPException(status_code=400, detail=f"Invalid digest type: {body.digest_type}")
    if body.mode not in ("facts", "full", "both"):
        raise HTTPException(status_code=400, detail=f"Invalid mode: {body.mode}")

    reload_settings()
    from src.analysis.llm_analyzer import reload_prompts
    reload_prompts()

    try:
        from src.digest.builder import DigestBuilder
        from src.digest.morning import build_morning_digest
        from src.digest.afternoon import build_afternoon_digest
        from src.digest.weekly import build_weekly_digest
        from src.digest.daytrade import build_daytrade_digest

        builders = {
            "morning": build_morning_digest,
            "afternoon": build_afternoon_digest,
            "weekly": build_weekly_digest,
            "daytrade": build_daytrade_digest,
        }

        builder = DigestBuilder()
        build_fn = builders[body.digest_type]

        # Capture digest data for action items if requested
        digest_data = {} if body.action_items else None

        if body.mode == "both":
            facts_content = build_fn(builder, mode="facts", out_data=digest_data)
            full_content = build_fn(builder, mode="full", out_data=digest_data)
            content = facts_content + "\n\n" + full_content
        elif body.mode == "full":
            content = build_fn(builder, mode="full", out_data=digest_data)
        else:
            content = build_fn(builder, mode="facts", out_data=digest_data)

        from src.digest.formatter import split_message
        messages = split_message(content)

        # Build action items if requested
        action_items_content = None
        if body.action_items and digest_data:
            from src.digest.action_items import build_action_items
            action_mode = "full" if body.mode in ("full", "both") else "facts"
            action_items_content = build_action_items(builder, body.digest_type, action_mode, digest_data)

        # Save to history
        _save_run_history(body.digest_type, body.mode, True, len(messages), body.dry_run)

        result = {
            "success": True,
            "content": content,
            "message_count": len(messages),
            "total_length": len(content),
        }
        if action_items_content:
            action_messages = split_message(action_items_content)
            result["action_items_content"] = action_items_content
            result["action_items_message_count"] = len(action_messages)
            result["action_items_length"] = len(action_items_content)

        return result

    except Exception as e:
        _save_run_history(body.digest_type, body.mode, False, 0, body.dry_run)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send")
def send_digest(body: DigestSendRequest):
    """Send digest content to Telegram."""
    try:
        from src.delivery.telegram_bot import TelegramDelivery
        delivery = TelegramDelivery()
        success = delivery.send_digest_sync(body.content)
        if success:
            return {"success": True, "message": "Digest sent to Telegram!"}
        return {"success": False, "message": "Some messages failed to send"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _save_run_history(digest_type: str, mode: str, success: bool, message_count: int, dry_run: bool) -> None:
    HISTORY_FILE.parent.mkdir(exist_ok=True)
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            history = []

    history.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": digest_type,
        "mode": mode,
        "success": success,
        "message_count": message_count,
        "dry_run": dry_run,
    })
    history = history[-100:]

    try:
        HISTORY_FILE.write_text(json.dumps(history, indent=2))
    except OSError:
        pass
