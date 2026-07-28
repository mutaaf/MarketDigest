"""Safe config manager — versioned writes with atomic operations and rollback."""

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

from src.innovation.safety import check_daily_budget, log_change, validate_param_change
from src.utils.logging_config import get_logger

logger = get_logger("innovation.config")

SIGNALS_YAML = Path(__file__).parent.parent.parent / "config" / "signals.yaml"
VERSIONS_DIR = Path(__file__).parent.parent.parent / "logs" / "innovation" / "versions"


def _save_version(reason: str = "") -> str:
    """Save current config as a version snapshot. Returns version_id."""
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    version_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = VERSIONS_DIR / f"{version_id}.yaml"
    shutil.copy2(SIGNALS_YAML, dest)

    # Write metadata
    meta = {
        "version_id": version_id,
        "timestamp": datetime.now().isoformat(),
        "reason": reason,
    }
    meta_path = VERSIONS_DIR / f"{version_id}.meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    logger.info(f"Config version saved: {version_id} ({reason})")
    return version_id


def safe_update_strategy_param(strategy: str, param: str, new_value: float,
                                reason: str, backtest_result: dict | None = None) -> dict:
    """Safely update a strategy parameter in signals.yaml.

    1. Validates against safety bounds
    2. Checks daily/weekly budget
    3. Saves version snapshot
    4. Writes atomically
    5. Logs the change

    Returns: {success, message, version_id, old_value, new_value}
    """
    # Load current config
    with open(SIGNALS_YAML) as f:
        config = yaml.safe_load(f)

    strategies = config.get("strategies", {})
    strat_config = strategies.get(strategy, {})
    old_value = strat_config.get(param)

    if old_value is None:
        return {"success": False, "message": f"Parameter {strategy}.{param} not found in config"}

    # Validate
    allowed, msg = validate_param_change(strategy, param, old_value, new_value)
    if not allowed:
        return {"success": False, "message": msg}

    # Check budget
    daily_ok, daily_remaining = check_daily_budget()
    if not daily_ok:
        return {"success": False, "message": "Daily change budget exhausted"}

    # Save version
    version_id = _save_version(f"Before changing {strategy}.{param}: {old_value} → {new_value}")

    # Update config
    config["strategies"][strategy][param] = new_value

    # Atomic write (write to temp, then rename)
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".yaml", dir=SIGNALS_YAML.parent)
        with os.fdopen(fd, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        os.replace(tmp_path, SIGNALS_YAML)
    except Exception as e:
        # Cleanup temp file if rename failed
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return {"success": False, "message": f"Write failed: {e}"}

    # Log the change
    log_change(strategy, param, old_value, new_value, reason, backtest_result)

    logger.info(f"Config updated: {strategy}.{param}: {old_value} → {new_value}")
    return {
        "success": True,
        "message": f"Updated {strategy}.{param}: {old_value} → {new_value}",
        "version_id": version_id,
        "old_value": old_value,
        "new_value": new_value,
    }


def safe_update_regime_overrides(overrides: dict, reason: str = "regime adaptation") -> dict:
    """Update regime_overrides section in signals.yaml."""
    with open(SIGNALS_YAML) as f:
        config = yaml.safe_load(f)

    version_id = _save_version(f"Before regime override update: {reason}")

    config["regime_overrides"] = overrides

    fd, tmp_path = tempfile.mkstemp(suffix=".yaml", dir=SIGNALS_YAML.parent)
    with os.fdopen(fd, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    os.replace(tmp_path, SIGNALS_YAML)

    logger.info(f"Regime overrides updated: {reason}")
    return {"success": True, "version_id": version_id}


def rollback(version_id: str) -> dict:
    """Rollback config to a specific version."""
    version_file = VERSIONS_DIR / f"{version_id}.yaml"
    if not version_file.exists():
        return {"success": False, "message": f"Version {version_id} not found"}

    # Save current as "pre-rollback" version
    _save_version(f"Pre-rollback to {version_id}")

    # Restore
    shutil.copy2(version_file, SIGNALS_YAML)
    logger.info(f"Config rolled back to version {version_id}")
    return {"success": True, "message": f"Rolled back to {version_id}"}


def list_versions(limit: int = 20) -> list[dict]:
    """List available config versions."""
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    versions = []
    for meta_file in sorted(VERSIONS_DIR.glob("*.meta.json"), reverse=True)[:limit]:
        try:
            with open(meta_file) as f:
                versions.append(json.load(f))
        except Exception:
            continue
    return versions
