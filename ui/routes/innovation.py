"""Innovation Agent API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/innovation", tags=["innovation"])


class ModeRequest(BaseModel):
    mode: str  # auto-tune | suggest | off


@router.get("/status")
async def get_status():
    """Get Innovation Agent status."""
    from src.innovation.agent import get_agent_status
    return get_agent_status()


@router.post("/start")
async def start_agent():
    """Start the Innovation Agent background thread."""
    from src.innovation.agent import start_agent
    start_agent()
    return {"status": "started"}


@router.post("/stop")
async def stop_agent():
    """Stop the Innovation Agent."""
    from src.innovation.agent import stop_agent
    stop_agent()
    return {"status": "stopped"}


@router.post("/mode")
async def set_mode(req: ModeRequest):
    """Set agent mode: auto-tune, suggest, or off."""
    from src.innovation.safety import set_mode
    try:
        set_mode(req.mode)
        return {"status": "ok", "mode": req.mode}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/daily-cycle")
async def run_daily():
    """Run daily learning cycle manually."""
    from src.innovation.agent import run_daily_cycle
    return run_daily_cycle()


@router.post("/weekly-cycle")
async def run_weekly():
    """Run weekly review manually."""
    from src.innovation.agent import run_weekly_cycle
    return run_weekly_cycle()


@router.get("/performance")
async def get_performance():
    """Get strategy performance metrics."""
    from src.innovation.learner import get_performance
    return get_performance()


@router.get("/changes")
async def get_changes(days: int = 30):
    """Get parameter change history."""
    from src.innovation.safety import get_change_history
    return {"changes": get_change_history(days)}


@router.get("/regime")
async def get_regime():
    """Get regime tracking data."""
    from src.innovation.regime_tracker import get_regime_summary
    return get_regime_summary()


@router.post("/rollback")
async def rollback(version_id: str):
    """Rollback config to a specific version."""
    from src.innovation.config_manager import rollback
    result = rollback(version_id)
    if not result["success"]:
        raise HTTPException(404, result["message"])
    return result


@router.get("/versions")
async def list_versions(limit: int = 20):
    """List available config versions for rollback."""
    from src.innovation.config_manager import list_versions
    return {"versions": list_versions(limit)}
