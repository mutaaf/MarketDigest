"""Config versioning — track changes to scoring weights and prompts over time."""

import json
from datetime import datetime
from pathlib import Path

import yaml

from config.settings import PROJECT_ROOT
from src.utils.logging_config import get_logger

logger = get_logger("retrace.versioning")

VERSIONS_DIR = PROJECT_ROOT / "logs" / "retrace" / "versions"


def _config_dir(config_name: str) -> Path:
    """Get directory for a config type's versions."""
    d = VERSIONS_DIR / config_name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _manifest_path(config_name: str) -> Path:
    return _config_dir(config_name) / "_manifest.json"


def _load_manifest(config_name: str) -> list[dict]:
    path = _manifest_path(config_name)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def _save_manifest(config_name: str, manifest: list[dict]) -> None:
    path = _manifest_path(config_name)
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)


def save_version(config_name: str, content: dict, description: str = "") -> str:
    """Save a new version of a config. Returns the version ID (timestamp string)."""
    now = datetime.now()
    version_id = now.strftime("%Y-%m-%dT%H-%M-%S")

    # Save content as YAML
    version_file = _config_dir(config_name) / f"{version_id}.yaml"
    with open(version_file, "w") as f:
        yaml.dump(content, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    # Update manifest
    manifest = _load_manifest(config_name)
    manifest.append({
        "version_id": version_id,
        "timestamp": now.isoformat(),
        "description": description or f"{config_name} updated",
    })
    _save_manifest(config_name, manifest)

    logger.info(f"Version saved: {config_name}/{version_id} — {description}")
    return version_id


def list_versions(config_name: str, limit: int = 50) -> list[dict]:
    """List versions for a config, newest first."""
    manifest = _load_manifest(config_name)
    return list(reversed(manifest))[:limit]


def get_version(config_name: str, version_id: str) -> dict | None:
    """Load a specific version's content."""
    version_file = _config_dir(config_name) / f"{version_id}.yaml"
    if not version_file.exists():
        return None
    with open(version_file) as f:
        content = yaml.safe_load(f) or {}
    manifest = _load_manifest(config_name)
    entry = next((e for e in manifest if e["version_id"] == version_id), None)
    return {
        "version_id": version_id,
        "content": content,
        "timestamp": entry["timestamp"] if entry else None,
        "description": entry["description"] if entry else "",
    }


def diff_versions(config_name: str, version_a: str, version_b: str) -> dict:
    """Compare two versions, returning list of changed keys."""
    a = get_version(config_name, version_a)
    b = get_version(config_name, version_b)
    if not a or not b:
        return {"error": "Version not found", "changes": []}

    a_content = a["content"]
    b_content = b["content"]

    # Flatten for comparison
    def _flatten(d, prefix=""):
        items = {}
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                items.update(_flatten(v, key))
            else:
                items[key] = v
        return items

    flat_a = _flatten(a_content)
    flat_b = _flatten(b_content)
    all_keys = sorted(set(flat_a.keys()) | set(flat_b.keys()))

    changes = []
    for key in all_keys:
        old = flat_a.get(key)
        new = flat_b.get(key)
        if old != new:
            changes.append({"key": key, "old": old, "new": new})

    return {
        "version_a": version_a,
        "version_b": version_b,
        "changes": changes,
    }


def rollback(config_name: str, version_id: str) -> str:
    """Rollback a config to a previous version.

    Saves current state as a new version (labelled 'Rollback to X'),
    then overwrites the live config with the old version's content.
    Returns the new version ID.
    """
    old = get_version(config_name, version_id)
    if not old:
        raise ValueError(f"Version {version_id} not found for {config_name}")

    # Save current as new version before overwriting
    if config_name == "scoring":
        from src.retrace.scoring_config import load_scoring_weights, SCORING_YAML
        current = {"weights": load_scoring_weights(), "description": "Pre-rollback state"}
        new_id = save_version(config_name, current, f"Rollback to {version_id}")
        # Write old content back to live config
        with open(SCORING_YAML, "w") as f:
            yaml.dump(old["content"], f, default_flow_style=False, sort_keys=False)
    elif config_name == "prompts":
        from ui.routes.prompts import _load_prompts_yaml, PROMPTS_YAML
        current = _load_prompts_yaml()
        new_id = save_version(config_name, current, f"Rollback to {version_id}")
        with open(PROMPTS_YAML, "w") as f:
            yaml.dump(old["content"], f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        # Reload prompts in memory
        try:
            from src.analysis.llm_analyzer import reload_prompts
            reload_prompts()
        except Exception:
            pass
    else:
        raise ValueError(f"Unknown config type: {config_name}")

    logger.info(f"Rolled back {config_name} to {version_id}")
    return new_id


def get_current_version_id(config_name: str) -> str | None:
    """Get the latest version ID for a config, or None if no versions exist."""
    manifest = _load_manifest(config_name)
    if manifest:
        return manifest[-1]["version_id"]
    return None
