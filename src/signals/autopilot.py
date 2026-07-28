"""Autopilot engine — runs signal scanning, auto paper-trading, position monitoring, and alerts.

This is the brain of Signal Forge. It runs on a loop and:
1. Scans all instruments for signals every N minutes
2. Rates each signal TAKE / WATCH / SKIP
3. Auto paper-trades TAKE signals
4. Monitors open positions and closes at stop/target
5. Sends Telegram alerts for every action
6. Tracks daily P&L and pauses if daily limit hit
"""

import asyncio
import json
import threading
import time
from datetime import date, datetime
from pathlib import Path

import yaml

from src.signals.engine import scan_signals
from src.signals.models import Signal
from src.trading.paper_engine import (
    check_open_trades,
    get_paper_portfolio,
    paper_enter_trade,
)
from src.trading.risk_manager import get_risk_dashboard, validate_trade
from src.utils.logging_config import get_logger

logger = get_logger("autopilot")

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "signals.yaml"
RISK_PATH = Path(__file__).parent.parent.parent / "config" / "risk.yaml"
STATE_PATH = Path(__file__).parent.parent.parent / "logs" / "autopilot_state.json"


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _load_risk() -> dict:
    with open(RISK_PATH) as f:
        return yaml.safe_load(f)


# ── Signal Rating ────────────────────────────────────────────────────

def rate_signal(signal: Signal) -> str:
    """Rate a signal as TAKE, WATCH, or SKIP.

    TAKE: High confidence (>=65), R/R >= 2.0, conditions met >= 3
    WATCH: Medium confidence (50-65) or R/R between 1.5-2.0
    SKIP: Low confidence (<50) or R/R < 1.5 or fails risk validation
    """
    score = signal.confluence_score
    rr = signal.risk_reward
    conditions = len(signal.conditions_met or [])

    # Hard skips
    if rr < 1.5:
        return "SKIP"
    if score < 40:
        return "SKIP"

    # TAKE conditions
    if score >= 65 and rr >= 2.0 and conditions >= 3:
        return "TAKE"
    if score >= 70 and rr >= 1.8:
        return "TAKE"
    if score >= 80:
        return "TAKE"

    # WATCH
    if score >= 50 or (rr >= 2.0 and conditions >= 2):
        return "WATCH"

    return "SKIP"


# ── Telegram Alerts ──────────────────────────────────────────────────

def _format_signal_alert(signal: Signal, rating: str) -> str:
    """Format a signal for Telegram."""
    from src.digest.formatter import bold, code, esc

    arrow = "🟢 BUY" if signal.direction == "BUY" else "🔴 SELL"
    rating_emoji = {"TAKE": "✅", "WATCH": "👀", "SKIP": "⏭️"}.get(rating, "❓")

    lines = [
        f"{rating_emoji} <b>{rating}</b> — {arrow} {bold(signal.symbol)}",
        f"Strategy: {esc(signal.strategy_name or '?')} | Regime: {esc(signal.regime or '?')}",
        f"Entry: {code(str(signal.entry_price))} | Stop: {code(str(signal.stop_loss))} | Target: {code(str(signal.target_1))}",
        f"R/R: {code(str(signal.risk_reward) + ':1')} | Grade: {code(signal.grade)} ({signal.confluence_score:.0f}/100)",
    ]

    if signal.position_size:
        lines.append(f"Risk: {code('$' + str(signal.position_size.dollar_risk))} → Reward: {code('$' + str(signal.position_size.dollar_reward))}")

    # Timing info
    timing = signal.timing
    if timing:
        lines.append("")
        lines.append(f"⏱ Hold: {bold(esc(timing.get('hold_duration', '?')))} ({esc(timing.get('time_horizon', '?'))})")
        urgency = timing.get("urgency", "")
        if urgency:
            lines.append(f"⚡ {esc(urgency)}")
        when_to_exit = timing.get("when_to_exit", "")
        if when_to_exit:
            lines.append(f"🚪 Exit: {esc(when_to_exit)}")

    if signal.conditions_met:
        conds = "\n".join(f"  ✓ {esc(c)}" for c in signal.conditions_met[:4])
        lines.append(f"\n{conds}")

    asset = "FOREX (manual on TastyFX)" if signal.asset_type == "forex" else "OPTIONS (Tastytrade)"
    lines.append(f"\n<i>{asset}</i>")

    return "\n".join(lines)


def _format_trade_alert(action: str, symbol: str, direction: str, price: float,
                        pnl: float = 0, r_multiple: float = 0, reason: str = "",
                        timing: dict | None = None) -> str:
    """Format a trade entry/exit for Telegram."""
    from src.digest.formatter import bold, code, esc

    if action == "ENTRY":
        arrow = "🟢" if direction == "BUY" else "🔴"
        line = f"{arrow} <b>PAPER {direction} {bold(symbol)}</b> @ {code(str(price))}"
        if timing:
            hold = timing.get("hold_duration", "")
            exit_plan = timing.get("when_to_exit", "")
            if hold:
                line += f"\n⏱ Hold: {bold(esc(hold))}"
            if exit_plan:
                line += f"\n🚪 Exit: {esc(exit_plan)}"
        return line
    else:  # EXIT
        emoji = "💰" if pnl >= 0 else "❌"
        outcome = "WIN" if pnl >= 0 else "LOSS"
        return (
            f"{emoji} <b>CLOSED {bold(symbol)}</b> @ {code(str(price))}\n"
            f"P&L: {code(f'${pnl:+.2f}')} ({r_multiple:+.1f}R) — {outcome}\n"
            f"Reason: {reason}"
        )


def _format_daily_summary(portfolio: dict, signals_count: int, trades_today: int) -> str:
    """Format end-of-day summary for Telegram."""
    from src.digest.formatter import code

    lines = [
        "\n📊 <b>Signal Forge — Daily Summary</b>",
        "",
    ]

    for key in ("forex", "options"):
        acct = portfolio.get(key, {})
        stats = acct.get("stats", {})
        bal = acct.get("balance", 500)
        ret = acct.get("return_pct", 0)
        wr = stats.get("win_rate", 0)
        total = stats.get("total_trades", 0)
        lines.append(f"<b>{key.upper()}</b>: {code(f'${bal:.2f}')} ({ret:+.1f}%) | {total} trades | {wr:.0f}% WR")

    lines.extend([
        "",
        f"Signals scanned today: {code(str(signals_count))}",
        f"Trades executed today: {code(str(trades_today))}",
    ])

    return "\n".join(lines)


async def _send_telegram(message: str):
    """Send a Telegram message using the existing delivery system."""
    try:
        from src.delivery.telegram_bot import TelegramDelivery
        delivery = TelegramDelivery()
        await delivery.send_digest(message)
        logger.info(f"Telegram alert sent ({len(message)} chars)")
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")


def _send_telegram_sync(message: str):
    """Sync wrapper for Telegram send."""
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_send_telegram(message))
        loop.close()
    except Exception as e:
        logger.warning(f"Telegram sync send failed: {e}")


# ── Position Monitor ─────────────────────────────────────────────────

def _get_current_prices() -> dict[str, float]:
    """Fetch current prices for all signal instruments."""
    import yfinance as yf
    config = _load_config()
    prices = {}

    ticker_map = {}
    for group in config.get("signal_instruments", {}).values():
        for inst in group:
            ticker_map[inst["symbol"]] = inst.get("yfinance", inst["symbol"])

    for symbol, yf_sym in ticker_map.items():
        try:
            t = yf.Ticker(yf_sym)
            info = t.fast_info
            price = getattr(info, 'last_price', None) or getattr(info, 'previous_close', None)
            if price:
                prices[symbol] = float(price)
        except Exception:
            continue

    return prices


def monitor_positions() -> list[dict]:
    """Check open positions against current prices and auto-close if stop/target hit."""
    prices = _get_current_prices()
    closed = check_open_trades(prices)

    for result in closed:
        if result.get("success"):
            msg = _format_trade_alert(
                "EXIT", result.get("symbol", "?"), "",
                0, result.get("pnl", 0), result.get("r_multiple", 0),
                result.get("message", "Auto-closed"),
            )
            _send_telegram_sync(msg)

    return closed


# ── Autopilot Loop ───────────────────────────────────────────────────

def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_scan": None, "signals_today": 0, "trades_today": 0,
            "date": str(date.today()), "running": False}


def _save_state(state: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2, default=str)


def run_scan_cycle() -> dict:
    """Run one complete scan cycle: scan → rate → trade → monitor → alert.

    Returns dict with cycle results.
    """
    state = _load_state()
    if state.get("date") != str(date.today()):
        state = {"last_scan": None, "signals_today": 0, "trades_today": 0,
                 "date": str(date.today()), "running": state.get("running", False)}

    results = {
        "timestamp": datetime.now().isoformat(),
        "signals": [],
        "trades_entered": [],
        "trades_closed": [],
        "alerts_sent": 0,
    }

    # 1. Scan for signals
    logger.info("Autopilot: scanning markets...")
    try:
        signals = scan_signals()
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        return results

    results["signals_count"] = len(signals)
    state["signals_today"] += len(signals)
    state["last_scan"] = datetime.now().isoformat()

    # 2. Rate and alert on TAKE signals
    take_signals = []
    watch_signals = []

    for signal in signals:
        rating = rate_signal(signal)
        signal_info = {
            "symbol": signal.symbol,
            "direction": signal.direction,
            "strategy": signal.strategy_name,
            "rating": rating,
            "score": signal.confluence_score,
            "rr": signal.risk_reward,
        }
        results["signals"].append(signal_info)

        if rating == "TAKE":
            take_signals.append(signal)
            # Send Telegram alert
            msg = _format_signal_alert(signal, rating)
            _send_telegram_sync(msg)
            results["alerts_sent"] += 1

        elif rating == "WATCH":
            watch_signals.append(signal)

    # 3. Auto paper-trade TAKE signals
    for signal in take_signals:
        asset_key = "forex" if signal.asset_type == "forex" else "options"
        dollar_risk = signal.position_size.dollar_risk if signal.position_size else 10.0

        # Validate risk
        validation = validate_trade(asset_key, dollar_risk)
        if not validation["allowed"]:
            logger.info(f"Autopilot: skipping {signal.symbol} — {validation['reason']}")
            continue

        result = paper_enter_trade(signal)
        if result.get("success"):
            results["trades_entered"].append({
                "symbol": signal.symbol,
                "direction": signal.direction,
                "entry": signal.entry_price,
            })
            state["trades_today"] += 1

            # Alert
            msg = _format_trade_alert("ENTRY", signal.symbol, signal.direction, signal.entry_price,
                                      timing=signal.timing)
            _send_telegram_sync(msg)
            results["alerts_sent"] += 1

    # 4. Monitor open positions
    closed = monitor_positions()
    results["trades_closed"] = closed

    # 5. Summary if we found TAKE signals
    if take_signals:
        logger.info(f"Autopilot: {len(take_signals)} TAKE signals, "
                     f"{len(results['trades_entered'])} trades entered, "
                     f"{len(closed)} positions closed")

    _save_state(state)
    return results


def send_daily_summary():
    """Send end-of-day performance summary via Telegram."""
    state = _load_state()
    portfolio = get_paper_portfolio()
    msg = _format_daily_summary(
        portfolio,
        state.get("signals_today", 0),
        state.get("trades_today", 0),
    )
    _send_telegram_sync(msg)


def get_autopilot_status() -> dict:
    """Get current autopilot state for UI display."""
    state = _load_state()
    portfolio = get_paper_portfolio()
    risk = get_risk_dashboard()

    return {
        "running": state.get("running", False),
        "last_scan": state.get("last_scan"),
        "signals_today": state.get("signals_today", 0),
        "trades_today": state.get("trades_today", 0),
        "portfolio": portfolio,
        "risk": risk,
        "date": state.get("date"),
    }


# ── Background Runner ────────────────────────────────────────────────

_autopilot_thread: threading.Thread | None = None
_autopilot_stop = threading.Event()


def start_autopilot(interval_minutes: int = 5):
    """Start the autopilot background loop."""
    global _autopilot_thread

    if _autopilot_thread and _autopilot_thread.is_alive():
        logger.warning("Autopilot already running")
        return

    state = _load_state()
    state["running"] = True
    _save_state(state)
    _autopilot_stop.clear()

    def _loop():
        logger.info(f"Autopilot started (scanning every {interval_minutes}min)")
        _send_telegram_sync("🤖 <b>Signal Forge Autopilot STARTED</b>\n"
                            f"Scanning every {interval_minutes} minutes.\n"
                            "I'll alert you for TAKE signals and auto paper-trade them.")

        while not _autopilot_stop.is_set():
            try:
                run_scan_cycle()
            except Exception as e:
                logger.error(f"Autopilot cycle error: {e}")

            # Wait for next cycle (check stop flag every 10s)
            for _ in range(interval_minutes * 6):
                if _autopilot_stop.is_set():
                    break
                time.sleep(10)

        state = _load_state()
        state["running"] = False
        _save_state(state)
        logger.info("Autopilot stopped")

    _autopilot_thread = threading.Thread(target=_loop, daemon=True, name="autopilot")
    _autopilot_thread.start()


def stop_autopilot():
    """Stop the autopilot background loop."""
    _autopilot_stop.set()
    state = _load_state()
    state["running"] = False
    _save_state(state)
    _send_telegram_sync("🛑 <b>Signal Forge Autopilot STOPPED</b>")
    logger.info("Autopilot stop requested")
