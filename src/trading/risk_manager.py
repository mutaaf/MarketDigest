"""Risk manager — enforces position limits, daily loss limits, and trade validation."""

import json
from datetime import date
from pathlib import Path

import yaml

from src.utils.logging_config import get_logger

logger = get_logger("risk_manager")

RISK_PATH = Path(__file__).parent.parent.parent / "config" / "risk.yaml"
STATE_PATH = Path(__file__).parent.parent.parent / "logs" / "risk_state.json"


def _load_risk() -> dict:
    with open(RISK_PATH) as f:
        return yaml.safe_load(f)


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "forex": {"daily_pnl": 0.0, "date": str(date.today()), "open_positions": 0},
        "options": {"daily_pnl": 0.0, "date": str(date.today()), "open_positions": 0},
    }


def _save_state(state: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def _reset_if_new_day(state: dict) -> dict:
    today = str(date.today())
    for key in ("forex", "options"):
        if state.get(key, {}).get("date") != today:
            state[key] = {"daily_pnl": 0.0, "date": today, "open_positions": 0}
    return state


def validate_trade(asset_type: str, dollar_risk: float,
                   open_positions: int | None = None) -> dict:
    """Validate whether a new trade is allowed.

    Returns:
        {"allowed": bool, "reason": str, "warnings": list[str]}
    """
    risk_config = _load_risk()
    config = risk_config.get(asset_type, {})
    portfolio_config = risk_config.get("portfolio", {})
    state = _load_state()
    state = _reset_if_new_day(state)

    warnings = []
    asset_state = state.get(asset_type, {})
    balance = config.get("account_balance", 500.0)

    # Check daily loss limit
    daily_limit = balance * (config.get("daily_loss_limit_pct", 3.0) / 100)
    daily_pnl = asset_state.get("daily_pnl", 0.0)
    if daily_pnl <= -daily_limit:
        return {
            "allowed": False,
            "reason": f"Daily loss limit reached (${abs(daily_pnl):.2f} lost, limit ${daily_limit:.2f})",
            "warnings": [],
        }

    # Check max risk per trade
    max_risk = balance * (config.get("max_risk_per_trade_pct", 2.0) / 100)
    if dollar_risk > max_risk:
        return {
            "allowed": False,
            "reason": f"Risk ${dollar_risk:.2f} exceeds max ${max_risk:.2f} per trade",
            "warnings": [],
        }

    # Check concurrent positions
    current_positions = open_positions if open_positions is not None else asset_state.get("open_positions", 0)
    max_positions = config.get("max_concurrent_positions", 2)
    if current_positions >= max_positions:
        return {
            "allowed": False,
            "reason": f"Max {max_positions} concurrent positions reached",
            "warnings": [],
        }

    # Portfolio-level total risk check
    total_at_risk = abs(daily_pnl) + dollar_risk
    total_balance = sum(
        risk_config.get(k, {}).get("account_balance", 0)
        for k in ("forex", "options")
    )
    max_total_risk_pct = portfolio_config.get("max_total_risk_pct", 10.0)
    if total_at_risk > total_balance * (max_total_risk_pct / 100):
        warnings.append(f"Total portfolio risk approaching {max_total_risk_pct}% limit")

    # Warnings for approaching limits
    remaining_daily = daily_limit + daily_pnl  # pnl is negative
    if remaining_daily < daily_limit * 0.3:
        warnings.append(f"Only ${remaining_daily:.2f} daily risk remaining")

    return {"allowed": True, "reason": "Trade approved", "warnings": warnings}


def record_trade_result(asset_type: str, pnl: float, position_delta: int = 0):
    """Record a trade result (win/loss) and update daily P&L."""
    state = _load_state()
    state = _reset_if_new_day(state)

    asset_state = state.setdefault(asset_type, {
        "daily_pnl": 0.0, "date": str(date.today()), "open_positions": 0
    })
    asset_state["daily_pnl"] = round(asset_state.get("daily_pnl", 0.0) + pnl, 2)
    asset_state["open_positions"] = max(
        0, asset_state.get("open_positions", 0) + position_delta
    )

    _save_state(state)


def get_risk_dashboard() -> dict:
    """Get current risk state for dashboard display."""
    risk_config = _load_risk()
    state = _load_state()
    state = _reset_if_new_day(state)

    dashboard = {}
    for asset_type in ("forex", "options"):
        config = risk_config.get(asset_type, {})
        asset_state = state.get(asset_type, {})
        balance = config.get("account_balance", 500.0)
        daily_limit = balance * (config.get("daily_loss_limit_pct", 3.0) / 100)
        daily_pnl = asset_state.get("daily_pnl", 0.0)

        dashboard[asset_type] = {
            "account_balance": balance,
            "daily_pnl": daily_pnl,
            "daily_limit": round(daily_limit, 2),
            "daily_risk_used_pct": round(abs(daily_pnl) / daily_limit * 100, 1) if daily_limit > 0 else 0,
            "open_positions": asset_state.get("open_positions", 0),
            "max_positions": config.get("max_concurrent_positions", 2),
            "max_risk_per_trade": round(balance * config.get("max_risk_per_trade_pct", 2.0) / 100, 2),
            "trading_paused": daily_pnl <= -daily_limit,
        }

    # Portfolio level
    total_balance = sum(d["account_balance"] for d in dashboard.values())
    total_pnl = sum(d["daily_pnl"] for d in dashboard.values())
    total_positions = sum(d["open_positions"] for d in dashboard.values())

    dashboard["portfolio"] = {
        "total_balance": total_balance,
        "total_daily_pnl": round(total_pnl, 2),
        "total_positions": total_positions,
        "total_risk_pct": round(abs(total_pnl) / total_balance * 100, 1) if total_balance > 0 else 0,
    }

    return dashboard
