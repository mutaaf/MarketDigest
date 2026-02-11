"""Daily/weekly % change calculations and rankings."""

from typing import Any

from src.utils.logging_config import get_logger

logger = get_logger("performance")


def compute_change(current: float, previous: float) -> dict[str, float]:
    """Compute absolute and percentage change."""
    if previous == 0:
        return {"change": 0.0, "change_pct": 0.0}
    change = current - previous
    change_pct = (change / previous) * 100
    return {"change": round(change, 4), "change_pct": round(change_pct, 2)}


def rank_by_performance(instruments: list[dict[str, Any]], key: str = "change_pct") -> list[dict[str, Any]]:
    """Sort instruments by performance metric, best first."""
    return sorted(instruments, key=lambda x: x.get(key, 0), reverse=True)


def get_top_movers(instruments: list[dict[str, Any]], n: int = 5) -> dict[str, list[dict[str, Any]]]:
    """Get top gainers and losers."""
    ranked = rank_by_performance(instruments)
    return {
        "gainers": ranked[:n],
        "losers": list(reversed(ranked[-n:])),
    }


def categorize_instruments(instruments: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group instruments by category and compute per-category stats."""
    categories: dict[str, list[dict[str, Any]]] = {}
    for inst in instruments:
        cat = inst.get("category", "other")
        categories.setdefault(cat, []).append(inst)
    return categories


def sector_comparison(instruments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare sector performance (avg % change per category)."""
    categories = categorize_instruments(instruments)
    sector_stats = []

    for cat_name, cat_instruments in categories.items():
        changes = [i.get("change_pct", 0) for i in cat_instruments if i.get("change_pct") is not None]
        if not changes:
            continue
        avg_change = sum(changes) / len(changes)
        best = max(cat_instruments, key=lambda x: x.get("change_pct", 0))
        worst = min(cat_instruments, key=lambda x: x.get("change_pct", 0))

        sector_stats.append({
            "sector": cat_name,
            "avg_change_pct": round(avg_change, 2),
            "best": {"name": best.get("name", ""), "change_pct": best.get("change_pct", 0)},
            "worst": {"name": worst.get("name", ""), "change_pct": worst.get("change_pct", 0)},
            "count": len(cat_instruments),
        })

    return sorted(sector_stats, key=lambda x: x["avg_change_pct"], reverse=True)


def weekly_performance_table(instruments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build weekly performance rankings table."""
    ranked = rank_by_performance(instruments, key="weekly_change_pct")
    for i, inst in enumerate(ranked):
        inst["rank"] = i + 1
    return ranked


def change_indicator(change_pct: float | None) -> str:
    """Return colored emoji indicator for price change."""
    if change_pct is None or (isinstance(change_pct, float) and change_pct != change_pct):
        return "⚪ 0.00%"
    if change_pct > 0:
        return f"🟢 +{change_pct:.2f}%"
    elif change_pct < 0:
        return f"🔴 {change_pct:.2f}%"
    return f"⚪ {change_pct:.2f}%"
