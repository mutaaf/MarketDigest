"""Innovation Agent — self-improving autonomous trading system.

Runs daily and weekly learning cycles to:
1. Track strategy performance from paper trade outcomes
2. Tune parameters via hill-climbing with backtest validation
3. Adapt to regime shifts by adjusting strategy emphasis
4. Report everything via Telegram
"""

import json
import threading
import time
from datetime import date, datetime
from pathlib import Path

from src.innovation.config_manager import safe_update_regime_overrides
from src.innovation.learner import get_performance, update_performance_ledger
from src.innovation.regime_tracker import (
    compute_regime_overrides,
    detect_regime_shift,
    get_regime_summary,
    track_regimes,
)
from src.innovation.reporter import format_daily_report, format_weekly_report, save_report
from src.innovation.safety import get_change_history, get_mode
from src.innovation.tuner import propose_and_apply
from src.utils.logging_config import get_logger

logger = get_logger("innovation.agent")

STATE_PATH = Path(__file__).parent.parent.parent / "logs" / "innovation" / "state.json"


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"running": False, "last_daily": None, "last_weekly": None,
            "cycles_run": 0, "date": str(date.today())}


def _save_state(state: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2, default=str)


def _send_telegram(message: str):
    """Send via existing Telegram delivery."""
    try:
        import asyncio

        from src.delivery.telegram_bot import TelegramDelivery
        delivery = TelegramDelivery()
        loop = asyncio.new_event_loop()
        loop.run_until_complete(delivery.send_digest(message))
        loop.close()
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")


# ── Learning Cycles ──────────────────────────────────────────────────

def run_daily_cycle() -> dict:
    """Run the daily learning cycle (after market close).

    1. Update performance ledger from trade outcomes
    2. Identify over/under-performers
    3. Tune parameters (if auto-tune mode)
    4. Track regime shifts and update overrides
    5. Send daily Telegram report
    """
    logger.info("Innovation Agent: starting daily cycle")
    state = _load_state()
    results = {"cycle": "daily", "timestamp": datetime.now().isoformat()}

    # Step 1: Update performance
    performance = update_performance_ledger()
    results["performance"] = performance.get("overall", {})

    # Step 2: Identify performers
    performers = performance.get("performers", {})
    results["outperformers"] = len(performers.get("outperformers", []))
    results["underperformers"] = len(performers.get("underperformers", []))

    # Step 3: Tune parameters (auto-tune mode only)
    changes = []
    if get_mode() == "auto-tune":
        changes = propose_and_apply()
        results["changes_applied"] = len(changes)
    else:
        results["changes_applied"] = 0
        results["mode"] = get_mode()

    # Step 4: Regime tracking
    # Get latest signals for regime tracking
    try:
        from src.signals.engine import get_latest_signals
        latest = get_latest_signals()
        track_regimes(latest)
    except Exception:
        pass

    regime_summary = get_regime_summary()
    shift = detect_regime_shift()
    results["regime_shift"] = shift is not None

    # Update regime overrides if shift detected
    if shift and get_mode() == "auto-tune":
        overrides = compute_regime_overrides()
        if overrides:
            safe_update_regime_overrides(overrides, shift.get("message", "regime shift"))
            results["regime_overrides_updated"] = True

    # Step 5: Send Telegram report
    try:
        report = format_daily_report(performance, changes, regime_summary, performers)
        save_report(report, "daily")
        _send_telegram(report)
        results["report_sent"] = True
    except Exception as e:
        logger.error(f"Report failed: {e}")
        results["report_sent"] = False

    # Update state
    state["last_daily"] = datetime.now().isoformat()
    state["cycles_run"] = state.get("cycles_run", 0) + 1
    _save_state(state)

    logger.info(f"Daily cycle complete: {results.get('changes_applied', 0)} changes, "
                f"report {'sent' if results.get('report_sent') else 'failed'}")
    return results


def run_weekly_cycle() -> dict:
    """Run the weekly deep review (Friday after close).

    Everything from daily cycle PLUS:
    - Full strategy ranking
    - Week's parameter changes summary
    - Deeper performance analysis
    """
    logger.info("Innovation Agent: starting weekly cycle")

    # Run daily cycle first
    daily_results = run_daily_cycle()

    # Additional weekly analysis
    performance = get_performance()
    performers = performance.get("performers", {})
    changes_week = get_change_history(days=7)
    regime_summary = get_regime_summary()

    # Weekly report
    try:
        report = format_weekly_report(performance, changes_week, regime_summary, performers)
        save_report(report, "weekly")
        _send_telegram(report)
    except Exception as e:
        logger.error(f"Weekly report failed: {e}")

    state = _load_state()
    state["last_weekly"] = datetime.now().isoformat()
    _save_state(state)

    logger.info("Weekly cycle complete")
    return {**daily_results, "cycle": "weekly", "changes_this_week": len(changes_week)}


# ── Agent Status ─────────────────────────────────────────────────────

def get_agent_status() -> dict:
    """Get current agent status for UI."""
    state = _load_state()
    performance = get_performance()
    regime = get_regime_summary()
    changes = get_change_history(days=7)

    return {
        "running": state.get("running", False),
        "mode": get_mode(),
        "last_daily": state.get("last_daily"),
        "last_weekly": state.get("last_weekly"),
        "cycles_run": state.get("cycles_run", 0),
        "performance": performance.get("overall", {}),
        "strategies": performance.get("strategies_30d", {}),
        "performers": performance.get("performers", {}),
        "regime": regime,
        "recent_changes": changes[:10],
    }


# ── Background Runner ────────────────────────────────────────────────

_agent_thread: threading.Thread | None = None
_agent_stop = threading.Event()


def start_agent():
    """Start the Innovation Agent background thread.

    Runs daily cycle at scheduled time, weekly on Fridays.
    """
    global _agent_thread

    if _agent_thread and _agent_thread.is_alive():
        logger.warning("Innovation Agent already running")
        return

    state = _load_state()
    state["running"] = True
    _save_state(state)
    _agent_stop.clear()

    def _loop():
        logger.info("Innovation Agent started")
        mode = get_mode()
        _send_telegram(f"🧠 <b>Innovation Agent STARTED</b> (mode: {mode})\n"
                       f"I'll learn from your trades, tune strategies, and send daily reports.")

        while not _agent_stop.is_set():
            now = datetime.now()

            # Check if it's time for daily cycle (5 PM)
            if now.hour == 17 and now.minute < 10:
                state = _load_state()
                last = state.get("last_daily", "")
                if not last or last[:10] != str(date.today()):
                    try:
                        if now.weekday() == 4:  # Friday
                            run_weekly_cycle()
                        else:
                            run_daily_cycle()
                    except Exception as e:
                        logger.error(f"Cycle error: {e}")

            # Sleep 5 minutes between checks
            for _ in range(30):
                if _agent_stop.is_set():
                    break
                time.sleep(10)

        state = _load_state()
        state["running"] = False
        _save_state(state)
        logger.info("Innovation Agent stopped")

    _agent_thread = threading.Thread(target=_loop, daemon=True, name="innovation-agent")
    _agent_thread.start()


def stop_agent():
    """Stop the Innovation Agent."""
    _agent_stop.set()
    state = _load_state()
    state["running"] = False
    _save_state(state)
    _send_telegram("🧠 <b>Innovation Agent STOPPED</b>")
