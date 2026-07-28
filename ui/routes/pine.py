"""Pine Script API routes."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/pine", tags=["pine"])


class GenerateRequest(BaseModel):
    strategy: str = "ema_crossover"
    custom_params: dict | None = None


@router.get("/strategies")
async def list_strategies():
    """List available Pine Script strategies."""
    from src.pine.generator import list_strategies
    return {"strategies": list_strategies()}


@router.post("/generate")
async def generate(req: GenerateRequest):
    """Generate a Pine Script strategy."""
    from src.pine.generator import generate_pine_script
    script = generate_pine_script(strategy=req.strategy, custom_params=req.custom_params)
    return {"strategy": req.strategy, "script": script}
