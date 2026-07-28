"""Reporter — format daily and weekly Telegram reports."""

from datetime import datetime
from pathlib import Path

from src.utils.logging_config import get_logger

logger = get_logger("innovation.reporter")

REPORTS_DIR = Path(__file__).parent.parent.parent / "logs" / "innovation" / "reports"


def format_daily_report(performance: dict, changes: list[dict],
                        regime_summary: dict, performers: dict) -> str:
    """Format the daily Innovation Agent report for Telegram."""
    from src.digest.formatter import code, esc

    overall = performance.get("overall", {})
    strategies = performance.get("strategies_30d", {})

    lines = [
        "\n🧠 <b>Innovation Agent — Daily Report</b>",
        "",
    ]

    # Overall stats
    total = overall.get("total_trades_30d", 0)
    pnl = overall.get("total_pnl_30d", 0)
    wr = overall.get("win_rate_30d", 0)
    lines.append(f"📊 <b>30-Day:</b> {code(str(total))} trades | "
                 f"{code(f'{wr:.0f}%')} WR | "
                 f"P&L: {code(f'${pnl:+.2f}')}")

    # Best and worst strategies
    if strategies:
        sorted_strats = sorted(strategies.items(), key=lambda x: x[1].get("total_pnl", 0), reverse=True)
        if sorted_strats:
            best = sorted_strats[0]
            lines.append(f"📈 <b>Best:</b> {esc(best[0])} ({best[1].get('win_rate', 0):.0f}% WR, "
                         f"${best[1].get('total_pnl', 0):+.2f})")
        if len(sorted_strats) > 1:
            worst = sorted_strats[-1]
            if worst[1].get("total_pnl", 0) < 0:
                lines.append(f"📉 <b>Worst:</b> {esc(worst[0])} ({worst[1].get('win_rate', 0):.0f}% WR, "
                             f"${worst[1].get('total_pnl', 0):+.2f})")

    # Changes applied
    if changes:
        lines.append("")
        lines.append(f"🔧 <b>CHANGES APPLIED ({len(changes)}):</b>")
        for i, c in enumerate(changes[:3], 1):
            lines.append(f"  {i}. {esc(c.get('strategy', '?'))}.{esc(c.get('param', '?'))}: "
                         f"{c.get('old_value', '?')} → {c.get('new_value', '?')}")
            if c.get("reason"):
                lines.append(f"     <i>{esc(c['reason'][:80])}</i>")

    # Regime
    if regime_summary.get("current"):
        current = regime_summary["current"]
        lines.append("")
        lines.append(f"🌐 <b>REGIME:</b> {esc(current.get('dominant', '?'))} "
                     f"({current.get('dominant_pct', 0):.0f}% of instruments)")
        shift = regime_summary.get("shift")
        if shift:
            lines.append(f"⚡ {esc(shift.get('message', 'Shift detected'))}")
        overrides = regime_summary.get("overrides", {})
        if overrides.get("note"):
            lines.append(f"   <i>{esc(overrides['note'])}</i>")

    # Recommendations
    under = performers.get("underperformers", [])
    if under:
        lines.append("")
        lines.append("💡 <b>RECOMMENDATION:</b>")
        for u in under[:2]:
            lines.append(f"  Consider tuning {esc(u['strategy'])} — {esc(u.get('reason', ''))}")

    return "\n".join(lines)


def format_weekly_report(performance: dict, changes_week: list[dict],
                         regime_summary: dict, performers: dict) -> str:
    """Format comprehensive weekly report."""
    from src.digest.formatter import esc

    strategies = performance.get("strategies_30d", {})

    lines = [
        "\n🧠 <b>Innovation Agent — Weekly Review</b>",
        "",
    ]

    # Strategy rankings
    if strategies:
        lines.append("📈 <b>STRATEGY RANKINGS (30-day):</b>")
        sorted_strats = sorted(strategies.items(), key=lambda x: x[1].get("total_pnl", 0), reverse=True)
        for i, (name, m) in enumerate(sorted_strats, 1):
            emoji = "🟢" if m.get("total_pnl", 0) >= 0 else "🔴"
            lines.append(
                f"  {i}. {emoji} {esc(name)} — {m.get('wins', 0)}W/{m.get('losses', 0)}L, "
                f"${m.get('total_pnl', 0):+.2f}, {m.get('win_rate', 0):.0f}% WR"
            )

    # Changes this week
    if changes_week:
        lines.append("")
        lines.append(f"🔧 <b>PARAMETER CHANGES THIS WEEK: {len(changes_week)}</b>")
        for c in changes_week[:5]:
            lines.append(f"  • {esc(c.get('strategy', '?'))}.{esc(c.get('param', '?'))}: "
                         f"{c.get('old_value', '?')} → {c.get('new_value', '?')}")

    # Performers
    out = performers.get("outperformers", [])
    under = performers.get("underperformers", [])
    if out:
        lines.append("")
        lines.append("⭐ <b>OUTPERFORMERS:</b>")
        for o in out:
            lines.append(f"  {esc(o['strategy'])} — {esc(o.get('reason', ''))}")
    if under:
        lines.append("⚠️ <b>UNDERPERFORMERS:</b>")
        for u in under:
            lines.append(f"  {esc(u['strategy'])} — {esc(u.get('reason', ''))}")

    return "\n".join(lines)


def save_report(report: str, report_type: str = "daily"):
    """Archive a report to disk."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y-%m-%d')}_{report_type}.txt"
    with open(REPORTS_DIR / filename, "w") as f:
        f.write(report)
