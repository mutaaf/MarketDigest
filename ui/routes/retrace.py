"""Retrace endpoints — snapshots, grading, scoring, versioning."""

from fastapi import APIRouter, HTTPException, Query

from src.retrace.snapshot import list_snapshots, load_snapshot
from src.retrace.grader import grade_snapshot, aggregate_performance
from src.retrace.backfill import backfill_snapshot
from src.retrace.scoring_config import (
    load_scoring_weights, save_scoring_weights, validate_weights, DEFAULT_WEIGHTS,
)
from src.retrace.versioning import (
    list_versions, get_version, diff_versions, rollback,
    save_version, get_current_version_id,
)
from ui.models import ScoringWeightsUpdate, RollbackRequest

router = APIRouter(prefix="/api/retrace", tags=["retrace"])


# ── Snapshots ───────────────────────────────────────────────────

@router.get("/snapshots")
def get_snapshots(limit: int = Query(30, ge=1, le=200)):
    """List snapshot metadata, newest first."""
    return list_snapshots(limit=limit)


@router.get("/snapshots/{date}")
def get_snapshot(date: str):
    """Get full snapshot data for a date."""
    snapshot = load_snapshot(date)
    if not snapshot:
        raise HTTPException(404, f"No snapshot for {date}")
    return snapshot


# ── Backfill ───────────────────────────────────────────────────

@router.post("/backfill/{date}")
def backfill_date(date: str, overwrite: bool = Query(False)):
    """Generate a retroactive snapshot for a past date."""
    try:
        snapshot = backfill_snapshot(date, overwrite=overwrite)
        return {"success": True, "date": date, "pick_count": len(snapshot.get("top_picks", []))}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/backfill-and-grade/{date}")
def backfill_and_grade_date(date: str, overwrite: bool = Query(False)):
    """Generate a retroactive snapshot and immediately grade it."""
    try:
        snapshot = backfill_snapshot(date, overwrite=overwrite)
    except ValueError as e:
        raise HTTPException(400, str(e))

    result = grade_snapshot(snapshot)
    if "error" in result:
        return {"success": True, "date": date, "backfilled": True, "grading_error": result["error"]}

    return {
        "success": True,
        "date": date,
        "backfilled": True,
        "pick_count": len(snapshot.get("top_picks", [])),
        "grading": result,
    }


# ── Grading ─────────────────────────────────────────────────────

@router.post("/grade/{date}")
def grade_date(date: str):
    """Grade picks for a specific date against actual next-day prices."""
    snapshot = load_snapshot(date)
    if not snapshot:
        raise HTTPException(404, f"No snapshot for {date}")

    result = grade_snapshot(snapshot)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/grade-all")
def grade_all():
    """Grade all ungraded daytrade snapshots."""
    snapshots = list_snapshots(limit=200)
    results = {"graded": 0, "skipped": 0, "errors": []}

    for meta in snapshots:
        # Only grade daytrade snapshots (grading logic is daytrade-specific)
        if meta.get("digest_type", "daytrade") != "daytrade":
            results["skipped"] += 1
            continue
        if meta.get("has_grading"):
            results["skipped"] += 1
            continue

        snapshot = load_snapshot(meta["date"])
        if not snapshot:
            continue

        try:
            result = grade_snapshot(snapshot)
            if "error" in result:
                results["errors"].append({"date": meta["date"], "error": result["error"]})
            else:
                results["graded"] += 1
        except Exception as e:
            results["errors"].append({"date": meta["date"], "error": str(e)})

    return results


# ── Performance ─────────────────────────────────────────────────

@router.get("/performance")
def get_performance(days: int = Query(30, ge=1, le=365)):
    """Get aggregate performance stats across graded daytrade snapshots."""
    metas = list_snapshots(limit=200)
    snapshots = []
    for meta in metas:
        if meta.get("digest_type", "daytrade") != "daytrade":
            continue
        if meta.get("has_grading"):
            snap = load_snapshot(meta["date"])
            if snap:
                snapshots.append(snap)

    return aggregate_performance(snapshots, days=days)


# ── Scoring Weights ─────────────────────────────────────────────

@router.get("/scoring")
def get_scoring():
    """Get current scoring weights."""
    weights = load_scoring_weights()
    return {
        "weights": weights,
        "description": "Current scoring weights",
        "version": get_current_version_id("scoring"),
    }


@router.put("/scoring")
def update_scoring(body: ScoringWeightsUpdate):
    """Update scoring weights (validates sum=1.0, creates version)."""
    ok, msg = validate_weights(body.weights)
    if not ok:
        raise HTTPException(400, msg)

    save_scoring_weights(body.weights, body.description)
    return {"success": True, "weights": body.weights}


@router.post("/scoring/reset")
def reset_scoring():
    """Reset scoring weights to defaults."""
    save_scoring_weights(dict(DEFAULT_WEIGHTS), "Reset to defaults")
    return {"success": True, "weights": DEFAULT_WEIGHTS}


# ── Versioning ──────────────────────────────────────────────────

@router.get("/versions/{config_name}")
def get_versions(config_name: str, limit: int = Query(50, ge=1, le=200)):
    """List version history for a config type."""
    if config_name not in ("scoring", "prompts"):
        raise HTTPException(400, f"Unknown config type: {config_name}")
    return list_versions(config_name, limit=limit)


@router.get("/versions/{config_name}/diff")
def get_version_diff(config_name: str, a: str = Query(...), b: str = Query(...)):
    """Diff two versions of a config."""
    if config_name not in ("scoring", "prompts"):
        raise HTTPException(400, f"Unknown config type: {config_name}")
    result = diff_versions(config_name, a, b)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.get("/versions/{config_name}/{version_id}")
def get_version_detail(config_name: str, version_id: str):
    """Get a specific version's content."""
    if config_name not in ("scoring", "prompts"):
        raise HTTPException(400, f"Unknown config type: {config_name}")
    version = get_version(config_name, version_id)
    if not version:
        raise HTTPException(404, f"Version {version_id} not found")
    return version


@router.post("/versions/rollback")
def rollback_version(body: RollbackRequest):
    """Rollback a config to a previous version."""
    if body.config_name not in ("scoring", "prompts"):
        raise HTTPException(400, f"Unknown config type: {body.config_name}")
    try:
        new_id = rollback(body.config_name, body.version_id)
        return {"success": True, "new_version_id": new_id}
    except ValueError as e:
        raise HTTPException(404, str(e))
