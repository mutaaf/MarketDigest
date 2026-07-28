"""Risk management API routes."""

from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/risk", tags=["risk"])

RISK_PATH = Path(__file__).parent.parent.parent / "config" / "risk.yaml"


class RiskProfileUpdate(BaseModel):
    forex_balance: float | None = None
    forex_risk_per_trade_pct: float | None = None
    forex_daily_loss_limit_pct: float | None = None
    forex_max_positions: int | None = None
    forex_stop_multiplier: float | None = None
    options_balance: float | None = None
    options_risk_per_trade_pct: float | None = None
    options_daily_loss_limit_pct: float | None = None
    options_max_positions: int | None = None
    options_min_dte: int | None = None
    options_max_option_price: float | None = None
    portfolio_max_total_risk_pct: float | None = None


@router.get("/dashboard")
async def get_risk_dashboard():
    """Get full risk dashboard data."""
    from src.trading.risk_manager import get_risk_dashboard
    return get_risk_dashboard()


@router.post("/validate")
async def validate_trade(asset_type: str = "forex", dollar_risk: float = 10.0):
    """Validate whether a trade is allowed under risk rules."""
    from src.trading.risk_manager import validate_trade as _validate
    return _validate(asset_type, dollar_risk)


@router.get("/config")
async def get_risk_config():
    """Get current risk configuration."""
    with open(RISK_PATH) as f:
        return yaml.safe_load(f)


@router.put("/config")
async def update_risk_config(update: RiskProfileUpdate):
    """Update risk configuration. Only provided fields are changed."""
    with open(RISK_PATH) as f:
        config = yaml.safe_load(f)

    # Apply updates (only non-None fields)
    if update.forex_balance is not None:
        config["forex"]["account_balance"] = update.forex_balance
    if update.forex_risk_per_trade_pct is not None:
        if not 0.5 <= update.forex_risk_per_trade_pct <= 10:
            raise HTTPException(400, "Forex risk per trade must be 0.5-10%")
        config["forex"]["max_risk_per_trade_pct"] = update.forex_risk_per_trade_pct
    if update.forex_daily_loss_limit_pct is not None:
        if not 1 <= update.forex_daily_loss_limit_pct <= 20:
            raise HTTPException(400, "Daily loss limit must be 1-20%")
        config["forex"]["daily_loss_limit_pct"] = update.forex_daily_loss_limit_pct
    if update.forex_max_positions is not None:
        if not 1 <= update.forex_max_positions <= 10:
            raise HTTPException(400, "Max positions must be 1-10")
        config["forex"]["max_concurrent_positions"] = update.forex_max_positions
    if update.forex_stop_multiplier is not None:
        config["forex"]["stop_multiplier"] = update.forex_stop_multiplier

    if update.options_balance is not None:
        config["options"]["account_balance"] = update.options_balance
    if update.options_risk_per_trade_pct is not None:
        if not 1 <= update.options_risk_per_trade_pct <= 20:
            raise HTTPException(400, "Options risk per trade must be 1-20%")
        config["options"]["max_risk_per_trade_pct"] = update.options_risk_per_trade_pct
    if update.options_daily_loss_limit_pct is not None:
        if not 1 <= update.options_daily_loss_limit_pct <= 20:
            raise HTTPException(400, "Daily loss limit must be 1-20%")
        config["options"]["daily_loss_limit_pct"] = update.options_daily_loss_limit_pct
    if update.options_max_positions is not None:
        if not 1 <= update.options_max_positions <= 10:
            raise HTTPException(400, "Max positions must be 1-10")
        config["options"]["max_concurrent_positions"] = update.options_max_positions
    if update.options_min_dte is not None:
        config["options"]["min_days_to_expiry"] = update.options_min_dte
    if update.options_max_option_price is not None:
        config["options"]["max_option_price"] = update.options_max_option_price

    if update.portfolio_max_total_risk_pct is not None:
        if not 5 <= update.portfolio_max_total_risk_pct <= 50:
            raise HTTPException(400, "Portfolio total risk must be 5-50%")
        config["portfolio"]["max_total_risk_pct"] = update.portfolio_max_total_risk_pct

    # Write back
    with open(RISK_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    # Compute derived values for response
    fx_bal = config["forex"]["account_balance"]
    fx_pct = config["forex"]["max_risk_per_trade_pct"]
    opt_bal = config["options"]["account_balance"]
    opt_pct = config["options"]["max_risk_per_trade_pct"]

    return {
        "status": "updated",
        "config": config,
        "computed": {
            "forex_max_risk_per_trade": round(fx_bal * fx_pct / 100, 2),
            "forex_daily_limit": round(fx_bal * config["forex"]["daily_loss_limit_pct"] / 100, 2),
            "options_max_risk_per_trade": round(opt_bal * opt_pct / 100, 2),
            "options_daily_limit": round(opt_bal * config["options"]["daily_loss_limit_pct"] / 100, 2),
            "total_capital": fx_bal + opt_bal,
        },
    }
