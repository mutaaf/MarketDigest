"""Scoring weights configuration — load/save/validate from config/scoring.yaml."""


import yaml

from config.settings import PROJECT_ROOT

SCORING_YAML = PROJECT_ROOT / "config" / "scoring.yaml"

DEFAULT_WEIGHTS = {
    "rsi": 0.20,
    "trend": 0.15,
    "pivot": 0.20,
    "atr": 0.20,
    "volume": 0.15,
    "gap": 0.10,
}

WEIGHT_KEYS = sorted(DEFAULT_WEIGHTS.keys())


def load_scoring_weights() -> dict[str, float]:
    """Read scoring weights from YAML, falling back to defaults."""
    try:
        if SCORING_YAML.exists():
            with open(SCORING_YAML) as f:
                data = yaml.safe_load(f) or {}
            weights = data.get("weights", {})
            if set(weights.keys()) == set(WEIGHT_KEYS):
                return {k: float(weights[k]) for k in WEIGHT_KEYS}
    except Exception:
        pass
    return dict(DEFAULT_WEIGHTS)


def validate_weights(weights: dict[str, float]) -> tuple[bool, str]:
    """Validate scoring weights: all 6 keys, all >= 0, sum to 1.0."""
    if set(weights.keys()) != set(WEIGHT_KEYS):
        missing = set(WEIGHT_KEYS) - set(weights.keys())
        extra = set(weights.keys()) - set(WEIGHT_KEYS)
        parts = []
        if missing:
            parts.append(f"missing: {', '.join(sorted(missing))}")
        if extra:
            parts.append(f"unexpected: {', '.join(sorted(extra))}")
        return False, f"Invalid keys — {'; '.join(parts)}"

    for k, v in weights.items():
        if v < 0:
            return False, f"Weight '{k}' cannot be negative ({v})"

    total = sum(weights.values())
    if abs(total - 1.0) > 0.001:
        return False, f"Weights must sum to 1.0 (got {total:.4f})"

    return True, "OK"


DEFAULT_SWING_WEIGHTS = {"rsi": 0.25, "trend": 0.30, "pivot": 0.25, "atr": 0.20}
DEFAULT_LT_WEIGHTS_EQUITY = {"rsi": 0.10, "trend": 0.15, "pivot": 0.10, "atr": 0.05, "fundamentals": 0.60}
DEFAULT_LT_WEIGHTS_NON_EQUITY = {"rsi": 0.25, "trend": 0.35, "pivot": 0.25, "atr": 0.15}


def load_swing_weights() -> dict[str, float]:
    """Read swing scoring weights from YAML, falling back to defaults."""
    try:
        if SCORING_YAML.exists():
            with open(SCORING_YAML) as f:
                data = yaml.safe_load(f) or {}
            weights = data.get("swing_weights", {})
            if weights and all(k in weights for k in DEFAULT_SWING_WEIGHTS):
                return {k: float(weights[k]) for k in DEFAULT_SWING_WEIGHTS}
    except Exception:
        pass
    return dict(DEFAULT_SWING_WEIGHTS)


def load_longterm_weights(is_equity: bool = True) -> dict[str, float]:
    """Read long-term scoring weights from YAML, falling back to defaults."""
    key = "longterm_weights_equity" if is_equity else "longterm_weights_non_equity"
    defaults = DEFAULT_LT_WEIGHTS_EQUITY if is_equity else DEFAULT_LT_WEIGHTS_NON_EQUITY
    try:
        if SCORING_YAML.exists():
            with open(SCORING_YAML) as f:
                data = yaml.safe_load(f) or {}
            weights = data.get(key, {})
            if weights and all(k in weights for k in defaults):
                return {k: float(weights[k]) for k in defaults}
    except Exception:
        pass
    return dict(defaults)


def save_scoring_weights(weights: dict[str, float], description: str = "") -> None:
    """Validate and write scoring weights to YAML, then create a version."""
    ok, msg = validate_weights(weights)
    if not ok:
        raise ValueError(msg)

    data = {
        "weights": {k: round(weights[k], 4) for k in WEIGHT_KEYS},
        "description": description or "Scoring weights updated",
    }
    SCORING_YAML.parent.mkdir(parents=True, exist_ok=True)
    with open(SCORING_YAML, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    # Create version snapshot
    try:
        from src.retrace.versioning import save_version
        save_version("scoring", data, description or "Scoring weights updated")
    except Exception:
        pass
