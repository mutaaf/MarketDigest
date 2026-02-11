"""Digest run history endpoints."""

import json

from fastapi import APIRouter

from config.settings import PROJECT_ROOT

router = APIRouter(prefix="/api/history", tags=["history"])

HISTORY_FILE = PROJECT_ROOT / "logs" / "digest_history.json"


@router.get("")
def get_history(limit: int = 20):
    """Get recent digest run history."""
    if not HISTORY_FILE.exists():
        return []

    try:
        history = json.loads(HISTORY_FILE.read_text())
        return history[-limit:]
    except (json.JSONDecodeError, OSError):
        return []
