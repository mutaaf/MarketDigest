"""Memory + file-based JSON cache with TTL."""

import json
import math
import time
from pathlib import Path
from typing import Any

from config.settings import get_settings
from src.utils.logging_config import get_logger


def _sanitize_for_json(obj: Any) -> Any:
    """Recursively replace NaN/Infinity floats with None for JSON safety."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(item) for item in obj]
    return obj

logger = get_logger("cache")


class CacheManager:
    def __init__(self):
        self._memory: dict[str, dict[str, Any]] = {}
        self._cache_dir = get_settings().cache_dir
        self._cache_dir.mkdir(exist_ok=True)

    def get(self, key: str, max_age_seconds: int = 300) -> Any | None:
        """Get cached value. Check memory first, then file."""
        # Check memory cache
        if key in self._memory:
            entry = self._memory[key]
            if time.time() - entry["timestamp"] < max_age_seconds:
                return entry["data"]

        # Check file cache
        file_path = self._key_to_path(key)
        if file_path.exists():
            try:
                with open(file_path) as f:
                    entry = json.load(f)
                if time.time() - entry["timestamp"] < max_age_seconds:
                    # Promote to memory
                    self._memory[key] = entry
                    return entry["data"]
            except (json.JSONDecodeError, KeyError):
                logger.warning(f"Corrupt cache file: {file_path}")

        return None

    def get_stale(self, key: str) -> Any | None:
        """Get cached value even if expired (for fallback scenarios)."""
        if key in self._memory:
            return self._memory[key]["data"]

        file_path = self._key_to_path(key)
        if file_path.exists():
            try:
                with open(file_path) as f:
                    entry = json.load(f)
                return entry["data"]
            except (json.JSONDecodeError, KeyError):
                pass

        return None

    def set(self, key: str, data: Any, persist: bool = True) -> None:
        """Store value in memory and optionally to file."""
        entry = {"data": data, "timestamp": time.time()}
        self._memory[key] = entry

        if persist:
            file_path = self._key_to_path(key)
            try:
                safe_entry = _sanitize_for_json(entry)
                with open(file_path, "w") as f:
                    json.dump(safe_entry, f, default=str)
            except (TypeError, OSError) as e:
                logger.warning(f"Failed to persist cache for {key}: {e}")

    def _key_to_path(self, key: str) -> Path:
        safe_key = key.replace("/", "_").replace(":", "_").replace(" ", "_")
        return self._cache_dir / f"{safe_key}.json"

    def clear_expired(self, max_age_seconds: int = 86400) -> int:
        """Remove expired file cache entries. Returns count of removed files."""
        removed = 0
        for file_path in self._cache_dir.glob("*.json"):
            try:
                with open(file_path) as f:
                    entry = json.load(f)
                if time.time() - entry.get("timestamp", 0) > max_age_seconds:
                    file_path.unlink()
                    removed += 1
            except (json.JSONDecodeError, KeyError, OSError):
                file_path.unlink(missing_ok=True)
                removed += 1
        return removed


# Global instance
cache = CacheManager()
