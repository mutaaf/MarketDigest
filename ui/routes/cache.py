"""Cache management endpoints."""

from fastapi import APIRouter

from config.settings import get_settings
from src.cache.manager import cache

router = APIRouter(prefix="/api/cache", tags=["cache"])


@router.get("/stats")
def cache_stats():
    """Get cache file statistics."""
    settings = get_settings()
    cache_dir = settings.cache_dir

    files = []
    total_size = 0

    if cache_dir.exists():
        for f in cache_dir.glob("*.json"):
            size = f.stat().st_size
            total_size += size
            files.append({
                "name": f.name,
                "size_bytes": size,
                "modified": f.stat().st_mtime,
            })

    files.sort(key=lambda x: x["modified"], reverse=True)

    return {
        "file_count": len(files),
        "total_size_bytes": total_size,
        "files": files[:50],
    }


@router.post("/clear")
def clear_cache():
    """Clear all cache files."""
    settings = get_settings()
    cache_dir = settings.cache_dir
    removed = 0

    if cache_dir.exists():
        for f in cache_dir.glob("*.json"):
            try:
                f.unlink()
                removed += 1
            except OSError:
                pass

    cache._memory.clear()
    return {"success": True, "removed": removed}


@router.post("/clear-expired")
def clear_expired():
    """Clear only expired cache files (older than 24h)."""
    removed = cache.clear_expired(max_age_seconds=86400)
    return {"success": True, "removed": removed}
