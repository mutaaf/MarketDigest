"""Safety guardrails for the Innovation Agent."""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from src.utils.logging_config import get_logger

logger = get_logger("innovation.safety")

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "innovation.yaml"
CHANGES_DIR = Path(__file__).parent.parent.parent / "logs" / "innovation" / "changes"

# Files the agent is FORBIDDEN from modifying
FORBIDDEN_FILES = {"risk.yaml"}

# Config keys the agent CANNOT touch
FORBIDDEN_KEYS = {
    "min_risk_reward", "trade_management", "signal_instruments",
    "backtest_gate", "paper_gate",
}


def load_innovation_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def get_mode() -> str:
    """Get current agent mode: auto-tune, suggest, or off."""
    cfg = load_innovation_config()
    return cfg.get("mode", "off")


def is_auto_tune() -> bool:
    return get_mode() == "auto-tune"


def set_mode(mode: str):
    """Set agent mode."""
    if mode not in ("auto-tune", "suggest", "off"):
        raise ValueError(f"Invalid mode: {mode}")
    cfg = load_innovation_config()
    cfg["mode"] = mode
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)


def validate_param_change(strategy: str, param: str, old_value: float,
                          new_value: float) -> tuple[bool, str]:
    """Validate a proposed parameter change against safety bounds.

    Returns (allowed, reason).
    """
    cfg = load_innovation_config()
    bounds = cfg.get("tunable_parameters", {}).get(strategy, {}).get(param)
    limits = cfg.get("rate_limits", {})

    if bounds is None:
        return False, f"Parameter {strategy}.{param} is not tunable"

    # Check bounds
    if new_value < bounds["min"] or new_value > bounds["max"]:
        return False, f"Value {new_value} outside bounds [{bounds['min']}, {bounds['max']}]"

    # Check max change %
    max_pct = limits.get("max_param_change_pct", 25)
    if old_value != 0:
        change_pct = abs(new_value - old_value) / abs(old_value) * 100
        if change_pct > max_pct:
            return False, f"Change of {change_pct:.0f}% exceeds max {max_pct}%"

    # Check cooling period
    cooling_days = limits.get("cooling_period_days", 3)
    recent_changes = _get_recent_changes(days=cooling_days)
    for change in recent_changes:
        if change.get("strategy") == strategy and change.get("param") == param:
            return False, f"Parameter {strategy}.{param} was changed {change['date']} — cooling period ({cooling_days} days)"

    return True, "OK"


def check_daily_budget() -> tuple[bool, int]:
    """Check if daily change budget allows more changes.

    Returns (allowed, remaining).
    """
    cfg = load_innovation_config()
    max_daily = cfg.get("rate_limits", {}).get("max_daily_changes", 3)
    today_changes = len([c for c in _get_recent_changes(days=1)
                         if c.get("date") == str(date.today())])
    remaining = max_daily - today_changes
    return remaining > 0, remaining


def check_weekly_budget() -> tuple[bool, int]:
    """Check weekly change budget."""
    cfg = load_innovation_config()
    max_weekly = cfg.get("rate_limits", {}).get("max_weekly_changes", 8)
    week_changes = len(_get_recent_changes(days=7))
    remaining = max_weekly - week_changes
    return remaining > 0, remaining


def log_change(strategy: str, param: str, old_value: float, new_value: float,
               reason: str, backtest_result: dict | None = None):
    """Log a parameter change."""
    CHANGES_DIR.mkdir(parents=True, exist_ok=True)
    change = {
        "timestamp": datetime.now().isoformat(),
        "date": str(date.today()),
        "strategy": strategy,
        "param": param,
        "old_value": old_value,
        "new_value": new_value,
        "reason": reason,
        "backtest_result": backtest_result,
    }
    filepath = CHANGES_DIR / f"{date.today()}_{strategy}_{param}.json"
    with open(filepath, "w") as f:
        json.dump(change, f, indent=2, default=str)
    logger.info(f"Change logged: {strategy}.{param}: {old_value} → {new_value} ({reason})")


def _get_recent_changes(days: int = 7) -> list[dict]:
    """Get changes from the last N days."""
    CHANGES_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = date.today() - timedelta(days=days)
    changes = []
    for fp in sorted(CHANGES_DIR.glob("*.json"), reverse=True):
        try:
            date_str = fp.stem.split("_")[0]
            if datetime.strptime(date_str, "%Y-%m-%d").date() < cutoff:
                break
            with open(fp) as f:
                changes.append(json.load(f))
        except Exception:
            continue
    return changes


def get_change_history(days: int = 30) -> list[dict]:
    """Get full change history for UI display."""
    return _get_recent_changes(days)
