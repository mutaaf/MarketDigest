"""Auto-tune scoring weights from retrace grading history.

Analyzes graded pick history to find weights that maximize the correlation
between composite scores and actual outcomes (R-multiples).
"""

import re
from typing import Any

import numpy as np
from scipy import optimize, stats

from src.analysis.daytrade_scorer import (
    _score_rsi, _score_trend, _score_atr, _score_volume, _score_gap,
)
from src.retrace.scoring_config import (
    WEIGHT_KEYS, load_scoring_weights, save_scoring_weights,
)
from src.retrace.snapshot import list_snapshots, load_snapshot
from src.utils.logging_config import get_logger

logger = get_logger("retrace.optimizer")


# ── Score recalculation ──────────────────────────────────────────


def recalculate_component_scores(pick: dict) -> dict[str, float]:
    """Recalculate the 6 component scores from raw snapshot pick data.

    Uses exact scoring functions for RSI/trend/volume, and approximations
    for ATR/pivot/gap when exact raw data isn't saved in the snapshot.
    """
    # Exact scores from raw values
    rsi_score = _score_rsi(pick.get("rsi"))
    trend_score = _score_trend(pick.get("trend"))
    volume_score = _score_volume(pick.get("volume_ratio"))

    # ATR: approximate from entry-stop distance if no atr_pct saved
    price = pick.get("price") or pick.get("entry") or 0
    atr_pct = pick.get("atr_pct")
    if atr_pct is not None:
        atr_score = _score_atr(atr_pct * price / 100 if price > 0 else None, price)
    else:
        # Approximate: atr ~ 2 * (entry - stop)
        entry = pick.get("entry", 0)
        stop = pick.get("stop", 0)
        if entry > 0 and stop > 0 and entry > stop:
            approx_atr = 2.0 * (entry - stop)
            atr_score = _score_atr(approx_atr, entry)
        else:
            atr_score = 40.0

    # Pivot: infer from signals
    pivot_score = _infer_pivot_score(pick.get("signals", []))

    # Gap: parse from signals
    gap_pct = pick.get("gap_pct")
    if gap_pct is None:
        gap_pct = _parse_gap_from_signals(pick.get("signals", []))
    gap_score = _score_gap(gap_pct, pick.get("volume_ratio"))

    # If component_scores were saved in snapshot, prefer those
    saved = pick.get("component_scores")
    if saved and isinstance(saved, dict) and len(saved) == 6:
        return {k: float(saved[k]) for k in WEIGHT_KEYS if k in saved}

    return {
        "rsi": rsi_score,
        "trend": trend_score,
        "pivot": pivot_score,
        "atr": atr_score,
        "volume": volume_score,
        "gap": gap_score,
    }


def _infer_pivot_score(signals: list[str]) -> float:
    """Infer pivot proximity score from signal strings."""
    for sig in signals:
        sig_lower = sig.lower()
        if "near s1" in sig_lower:
            return 90.0
        if "breaking r1" in sig_lower:
            return 85.0
    return 40.0


def _parse_gap_from_signals(signals: list[str]) -> float | None:
    """Parse gap percentage from signal strings like 'Gap up 1.2%'."""
    for sig in signals:
        m = re.search(r"Gap\s+(up|down)\s+([\d.]+)%", sig, re.IGNORECASE)
        if m:
            val = float(m.group(2))
            return val if m.group(1).lower() == "up" else -val
    return None


# ── Data collection ──────────────────────────────────────────────


def collect_graded_picks(min_picks: int = 30) -> tuple[list[dict], str]:
    """Scan all daytrade snapshots and collect picks with decided outcomes.

    Returns:
        (picks_list, status_message)
        Each pick dict has: symbol, r_multiple, outcome, component_scores,
        and original raw data (rsi, trend, signals, etc.)
    """
    metas = list_snapshots(limit=200)
    enriched_picks: list[dict] = []
    snapshots_used = 0

    for meta in metas:
        if meta.get("digest_type", "daytrade") != "daytrade":
            continue
        if not meta.get("has_grading"):
            continue

        snap = load_snapshot(meta["date"])
        if not snap or not snap.get("grading"):
            continue

        grading = snap["grading"]
        graded_picks = grading.get("picks", [])

        # Build lookup of original pick data
        all_picks = snap.get("top_picks", []) + snap.get("honorable_mentions", [])
        pick_lookup = {p.get("symbol"): p for p in all_picks}

        has_valid = False
        for gp in graded_picks:
            outcome = gp.get("outcome", "pending")
            if outcome not in ("win", "loss", "scratch"):
                continue
            r_mult = gp.get("r_multiple")
            if r_mult is None:
                continue

            symbol = gp.get("symbol", "")
            original = pick_lookup.get(symbol, {})

            # Merge graded pick data with original pick data
            merged = {**original, **gp}
            scores = recalculate_component_scores(merged)

            enriched_picks.append({
                "symbol": symbol,
                "outcome": outcome,
                "r_multiple": float(r_mult),
                "actual_return_pct": gp.get("actual_return_pct"),
                "mfe": gp.get("mfe"),
                "mae": gp.get("mae"),
                "component_scores": scores,
                "date": meta["date"],
            })
            has_valid = True

        if has_valid:
            snapshots_used += 1

    if len(enriched_picks) < min_picks:
        return enriched_picks, (
            f"Insufficient data: {len(enriched_picks)} graded picks found "
            f"(need {min_picks}). Grade more snapshots first."
        )

    return enriched_picks, f"Collected {len(enriched_picks)} picks from {snapshots_used} snapshots"


# ── Optimization ─────────────────────────────────────────────────


def _composite_score(weights: np.ndarray, scores_matrix: np.ndarray) -> np.ndarray:
    """Calculate composite scores given weights and a matrix of component scores."""
    return scores_matrix @ weights


def _objective(weights: np.ndarray, scores_matrix: np.ndarray,
               r_multiples: np.ndarray, top_k: int) -> float:
    """Composite objective to minimize (negative of goodness).

    0.5 * Spearman(composite, r_multiples)
    0.3 * normalized mean_R of top-K picks
    0.2 * normalized profit_factor
    """
    composites = _composite_score(weights, scores_matrix)
    n = len(composites)

    # Spearman correlation
    if n < 5:
        return 0.0
    corr, _ = stats.spearmanr(composites, r_multiples)
    if np.isnan(corr):
        corr = 0.0

    # Mean R of top-K picks (by composite score)
    k = min(top_k, n)
    top_indices = np.argsort(composites)[-k:]
    mean_r_top_k = np.mean(r_multiples[top_indices])
    # Normalize: clip to [-3, 3] range, scale to [0, 1]
    norm_mean_r = np.clip((mean_r_top_k + 3) / 6, 0, 1)

    # Profit factor (sum of wins / |sum of losses|)
    wins_sum = np.sum(r_multiples[r_multiples > 0])
    losses_sum = abs(np.sum(r_multiples[r_multiples < 0]))
    pf = wins_sum / max(losses_sum, 0.01)
    # Normalize: clip to [0, 5] and scale
    norm_pf = np.clip(pf / 5, 0, 1)

    # Combine (negative because we minimize)
    return -(0.5 * corr + 0.3 * norm_mean_r + 0.2 * norm_pf)


def _compute_metrics(weights: dict[str, float], picks: list[dict],
                     top_k: int) -> dict[str, float]:
    """Compute the three metric components for a given set of weights."""
    scores_matrix, r_multiples = _build_matrices(picks)
    w = np.array([weights[k] for k in WEIGHT_KEYS])
    composites = _composite_score(w, scores_matrix)
    n = len(composites)

    # Spearman
    corr = 0.0
    if n >= 5:
        c, _ = stats.spearmanr(composites, r_multiples)
        corr = float(c) if not np.isnan(c) else 0.0

    # Mean R top-K
    k = min(top_k, n)
    top_indices = np.argsort(composites)[-k:]
    mean_r = float(np.mean(r_multiples[top_indices]))

    # Profit factor
    wins_sum = float(np.sum(r_multiples[r_multiples > 0]))
    losses_sum = abs(float(np.sum(r_multiples[r_multiples < 0])))
    pf = wins_sum / max(losses_sum, 0.01)

    return {
        "spearman_correlation": round(corr, 4),
        "mean_r_top_k": round(mean_r, 4),
        "profit_factor": round(pf, 4),
    }


def _build_matrices(picks: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """Build scores matrix and r_multiples array from enriched picks."""
    scores_matrix = np.array([
        [p["component_scores"][k] for k in WEIGHT_KEYS]
        for p in picks
    ])
    r_multiples = np.array([p["r_multiple"] for p in picks])
    return scores_matrix, r_multiples


def optimize_weights(picks: list[dict], current_weights: dict[str, float],
                     min_weight: float = 0.02, max_weight: float = 0.60,
                     top_k: int = 10) -> dict[str, Any]:
    """Run SLSQP optimizer from multiple starting points.

    Returns dict with suggested_weights, metrics, weight_changes, etc.
    """
    scores_matrix, r_multiples = _build_matrices(picks)

    bounds = [(min_weight, max_weight)] * len(WEIGHT_KEYS)
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    # Starting points: current, uniform, perturbed
    current_arr = np.array([current_weights[k] for k in WEIGHT_KEYS])
    uniform_arr = np.ones(len(WEIGHT_KEYS)) / len(WEIGHT_KEYS)
    rng = np.random.default_rng(42)
    perturbed_arr = current_arr + rng.normal(0, 0.05, len(WEIGHT_KEYS))
    perturbed_arr = np.clip(perturbed_arr, min_weight, max_weight)
    perturbed_arr /= perturbed_arr.sum()

    starting_points = [current_arr, uniform_arr, perturbed_arr]
    best_result = None
    best_value = float("inf")

    for x0 in starting_points:
        result = optimize.minimize(
            _objective, x0,
            args=(scores_matrix, r_multiples, top_k),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 500, "ftol": 1e-10},
        )
        if result.fun < best_value:
            best_value = result.fun
            best_result = result

    # Build suggested weights dict
    suggested = {k: round(float(best_result.x[i]), 4) for i, k in enumerate(WEIGHT_KEYS)}
    # Ensure exact sum to 1.0
    diff = 1.0 - sum(suggested.values())
    suggested[WEIGHT_KEYS[0]] = round(suggested[WEIGHT_KEYS[0]] + diff, 4)

    # Metrics for current and suggested
    current_metrics = _compute_metrics(current_weights, picks, top_k)
    suggested_metrics = _compute_metrics(suggested, picks, top_k)

    # Weight changes
    weight_changes = {}
    for k in WEIGHT_KEYS:
        weight_changes[k] = {
            "current": round(current_weights[k], 4),
            "suggested": suggested[k],
            "change": round(suggested[k] - current_weights[k], 4),
        }

    return {
        "suggested_weights": suggested,
        "current_weights": {k: round(current_weights[k], 4) for k in WEIGHT_KEYS},
        "metrics": {
            "current": current_metrics,
            "suggested": suggested_metrics,
        },
        "weight_changes": weight_changes,
        "pick_count": len(picks),
        "optimization_converged": bool(best_result.success),
    }


# ── Indicator effectiveness ──────────────────────────────────────


def analyze_indicator_effectiveness(picks: list[dict]) -> list[dict]:
    """Per-indicator analysis: correlation with R-multiple, predictive power."""
    r_multiples = np.array([p["r_multiple"] for p in picks])
    results = []

    for i, key in enumerate(WEIGHT_KEYS):
        scores = np.array([p["component_scores"][key] for p in picks])

        # Spearman correlation with R-multiple
        if len(scores) >= 5 and np.std(scores) > 0:
            corr, p_val = stats.spearmanr(scores, r_multiples)
            corr = float(corr) if not np.isnan(corr) else 0.0
            p_val = float(p_val) if not np.isnan(p_val) else 1.0
        else:
            corr, p_val = 0.0, 1.0

        # Avg score for wins vs losses
        win_scores = [p["component_scores"][key] for p in picks if p["outcome"] == "win"]
        loss_scores = [p["component_scores"][key] for p in picks if p["outcome"] == "loss"]
        avg_win = float(np.mean(win_scores)) if win_scores else 0.0
        avg_loss = float(np.mean(loss_scores)) if loss_scores else 0.0

        # Median and spread
        median_score = float(np.median(scores))
        spread = float(np.std(scores))

        # Predictive win rate: win rate when score > median
        above_median = [p for p in picks if p["component_scores"][key] > median_score]
        if above_median:
            above_wins = sum(1 for p in above_median if p["outcome"] == "win")
            pred_wr = round(above_wins / len(above_median) * 100, 1)
        else:
            pred_wr = 0.0

        results.append({
            "name": key,
            "correlation_with_r": round(corr, 4),
            "p_value": round(p_val, 4),
            "avg_score_for_wins": round(avg_win, 1),
            "avg_score_for_losses": round(avg_loss, 1),
            "score_spread": round(spread, 1),
            "predictive_win_rate": pred_wr,
            "median_score": round(median_score, 1),
        })

    # Rank by absolute correlation
    results.sort(key=lambda x: abs(x["correlation_with_r"]), reverse=True)
    for rank, r in enumerate(results, 1):
        r["effectiveness_rank"] = rank

    return results


# ── Orchestrator ─────────────────────────────────────────────────


def run_optimization(min_picks: int = 30, top_k: int = 10) -> dict[str, Any]:
    """Full optimization pipeline: collect -> optimize -> analyze.

    Returns comprehensive results dict or error info.
    """
    picks, status = collect_graded_picks(min_picks=min_picks)

    if len(picks) < min_picks:
        return {
            "success": False,
            "error": status,
            "pick_count": len(picks),
        }

    current_weights = load_scoring_weights()

    try:
        optimization = optimize_weights(picks, current_weights, top_k=top_k)
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        return {
            "success": False,
            "error": f"Optimization failed: {e}",
            "pick_count": len(picks),
        }

    effectiveness = analyze_indicator_effectiveness(picks)

    # Data summary
    outcomes = {"win": 0, "loss": 0, "scratch": 0}
    for p in picks:
        outcomes[p["outcome"]] = outcomes.get(p["outcome"], 0) + 1

    dates = {p["date"] for p in picks}

    # Caveats
    caveats = []
    if len(picks) < 50:
        caveats.append(
            f"Small sample size ({len(picks)} picks). Results may not be statistically robust. "
            "Consider accumulating more graded data."
        )
    if not optimization.get("optimization_converged"):
        caveats.append("Optimizer did not fully converge. Suggested weights may be suboptimal.")
    if any(abs(c["change"]) > 0.15 for c in optimization["weight_changes"].values()):
        caveats.append(
            "Some weight changes are large (>15%). Consider applying gradually "
            "or running more data through the system first."
        )

    return {
        "success": True,
        "optimization": optimization,
        "indicator_effectiveness": effectiveness,
        "data_summary": {
            "total_picks": len(picks),
            "snapshots_used": len(dates),
            "outcomes": outcomes,
            "status": status,
        },
        "caveats": caveats,
    }
