"""Paper trading engine — simulates trades alongside live signals."""

import json
from datetime import datetime, date
from pathlib import Path
from typing import Literal

from src.signals.models import Signal
from src.trading.risk_manager import validate_trade, record_trade_result
from src.utils.logging_config import get_logger

logger = get_logger("paper_engine")

PAPER_LOG = Path(__file__).parent.parent.parent / "logs" / "paper_trades.json"
PAPER_PORTFOLIO = Path(__file__).parent.parent.parent / "logs" / "paper_portfolio.json"


def _load_portfolio() -> dict:
    if PAPER_PORTFOLIO.exists():
        try:
            with open(PAPER_PORTFOLIO) as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "forex": {
            "balance": 500.0,
            "initial_balance": 500.0,
            "open_trades": [],
            "stats": {"total_trades": 0, "wins": 0, "losses": 0, "total_pnl": 0.0},
        },
        "options": {
            "balance": 500.0,
            "initial_balance": 500.0,
            "open_trades": [],
            "stats": {"total_trades": 0, "wins": 0, "losses": 0, "total_pnl": 0.0},
        },
    }


def _save_portfolio(portfolio: dict):
    PAPER_PORTFOLIO.parent.mkdir(parents=True, exist_ok=True)
    with open(PAPER_PORTFOLIO, "w") as f:
        json.dump(portfolio, f, indent=2, default=str)


def _load_trade_log() -> list[dict]:
    if PAPER_LOG.exists():
        try:
            with open(PAPER_LOG) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_trade_log(trades: list[dict]):
    PAPER_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PAPER_LOG, "w") as f:
        json.dump(trades, f, indent=2, default=str)


def paper_enter_trade(signal: Signal) -> dict:
    """Enter a paper trade based on a signal.

    Returns:
        {"success": bool, "trade_id": str, "message": str}
    """
    portfolio = _load_portfolio()
    asset_key = "forex" if signal.asset_type == "forex" else "options"
    acct = portfolio[asset_key]

    # Validate risk
    dollar_risk = signal.dollar_risk if signal.position_size else 10.0
    open_count = len(acct["open_trades"])
    validation = validate_trade(asset_key, dollar_risk, open_count)

    if not validation["allowed"]:
        return {"success": False, "trade_id": "", "message": validation["reason"]}

    trade = {
        "id": signal.id,
        "signal_id": signal.id,
        "symbol": signal.symbol,
        "name": signal.name,
        "asset_type": signal.asset_type,
        "direction": signal.direction,
        "entry_price": signal.entry_price,
        "stop_loss": signal.stop_loss,
        "target_1": signal.target_1,
        "target_2": signal.target_2,
        "risk_reward": signal.risk_reward,
        "dollar_risk": dollar_risk,
        "position_size": signal.position_size.label if signal.position_size else "1 unit",
        "entry_time": datetime.now().isoformat(),
        "status": "open",
        "confluence_score": signal.confluence_score,
        "grade": signal.grade,
    }

    acct["open_trades"].append(trade)
    _save_portfolio(portfolio)

    # Log the entry
    log = _load_trade_log()
    log.append({**trade, "event": "entry"})
    _save_trade_log(log)

    logger.info(f"Paper {signal.direction} {signal.symbol} @ {signal.entry_price} "
                f"(risk ${dollar_risk:.2f}, R/R {signal.risk_reward})")

    return {
        "success": True,
        "trade_id": signal.id,
        "message": f"Paper {signal.direction} {signal.symbol} entered",
    }


def paper_close_trade(trade_id: str, exit_price: float,
                      reason: Literal["target_1", "target_2", "stop", "manual"] = "manual") -> dict:
    """Close a paper trade manually or by hitting target/stop.

    Returns:
        {"success": bool, "pnl": float, "r_multiple": float, "message": str}
    """
    portfolio = _load_portfolio()

    for asset_key in ("forex", "options"):
        acct = portfolio[asset_key]
        for trade in acct["open_trades"]:
            if trade["id"] == trade_id:
                # Calculate P&L
                entry = trade["entry_price"]
                direction = trade["direction"]
                dollar_risk = trade["dollar_risk"]

                if direction == "BUY":
                    price_pnl_pct = (exit_price - entry) / entry
                else:
                    price_pnl_pct = (entry - exit_price) / entry

                risk_distance = abs(entry - trade["stop_loss"])
                if risk_distance > 0:
                    r_multiple = (exit_price - entry) / risk_distance if direction == "BUY" \
                        else (entry - exit_price) / risk_distance
                else:
                    r_multiple = 0

                pnl = dollar_risk * r_multiple
                outcome = "win" if pnl > 0 else "loss"

                # Update portfolio
                acct["open_trades"].remove(trade)
                acct["balance"] = round(acct["balance"] + pnl, 2)
                acct["stats"]["total_trades"] += 1
                acct["stats"]["total_pnl"] = round(acct["stats"]["total_pnl"] + pnl, 2)
                if outcome == "win":
                    acct["stats"]["wins"] += 1
                else:
                    acct["stats"]["losses"] += 1

                _save_portfolio(portfolio)

                # Log the exit
                log = _load_trade_log()
                log.append({
                    **trade,
                    "event": "exit",
                    "exit_price": exit_price,
                    "exit_time": datetime.now().isoformat(),
                    "exit_reason": reason,
                    "pnl": round(pnl, 2),
                    "r_multiple": round(r_multiple, 2),
                    "outcome": outcome,
                })
                _save_trade_log(log)

                # Update risk state
                record_trade_result(asset_key, pnl, position_delta=-1)

                return {
                    "success": True,
                    "pnl": round(pnl, 2),
                    "r_multiple": round(r_multiple, 2),
                    "outcome": outcome,
                    "message": f"Closed {trade['symbol']} for ${pnl:+.2f} ({r_multiple:+.1f}R)",
                }

    return {"success": False, "pnl": 0, "r_multiple": 0, "message": "Trade not found"}


def check_open_trades(current_prices: dict[str, float]) -> list[dict]:
    """Check open paper trades against current prices for auto-close.

    Args:
        current_prices: {"USDJPY": 156.82, "SPY": 548.21, ...}

    Returns:
        List of closed trade results
    """
    portfolio = _load_portfolio()
    closed = []

    for asset_key in ("forex", "options"):
        acct = portfolio[asset_key]
        trades_to_check = list(acct["open_trades"])  # Copy to avoid mutation during iteration

        for trade in trades_to_check:
            symbol = trade["symbol"]
            price = current_prices.get(symbol)
            if price is None:
                continue

            direction = trade["direction"]
            stop = trade["stop_loss"]
            target = trade["target_1"]

            hit_stop = (direction == "BUY" and price <= stop) or \
                       (direction == "SELL" and price >= stop)
            hit_target = (direction == "BUY" and price >= target) or \
                         (direction == "SELL" and price <= target)

            if hit_stop:
                result = paper_close_trade(trade["id"], stop, "stop")
                closed.append(result)
            elif hit_target:
                result = paper_close_trade(trade["id"], target, "target_1")
                closed.append(result)

    return closed


def get_paper_portfolio() -> dict:
    """Get full paper trading portfolio state."""
    portfolio = _load_portfolio()

    # Add computed fields
    for asset_key in ("forex", "options"):
        acct = portfolio[asset_key]
        stats = acct["stats"]
        total = stats["total_trades"]
        if total > 0:
            stats["win_rate"] = round(stats["wins"] / total * 100, 1)
            stats["avg_pnl"] = round(stats["total_pnl"] / total, 2)
        else:
            stats["win_rate"] = 0.0
            stats["avg_pnl"] = 0.0
        acct["return_pct"] = round(
            (acct["balance"] - acct["initial_balance"]) / acct["initial_balance"] * 100, 1
        )

    # Graduation check
    gate_passed = all(
        portfolio[k]["stats"]["total_trades"] >= 50 and
        portfolio[k]["stats"].get("win_rate", 0) >= 50.0
        for k in ("forex", "options")
    )
    portfolio["ready_for_live"] = gate_passed

    return portfolio


def get_trade_journal(limit: int = 50) -> list[dict]:
    """Get recent trade journal entries."""
    log = _load_trade_log()
    exits = [t for t in log if t.get("event") == "exit"]
    return exits[-limit:]


def reset_paper_portfolio():
    """Reset paper portfolio to initial state."""
    portfolio = {
        "forex": {
            "balance": 500.0,
            "initial_balance": 500.0,
            "open_trades": [],
            "stats": {"total_trades": 0, "wins": 0, "losses": 0, "total_pnl": 0.0},
        },
        "options": {
            "balance": 500.0,
            "initial_balance": 500.0,
            "open_trades": [],
            "stats": {"total_trades": 0, "wins": 0, "losses": 0, "total_pnl": 0.0},
        },
    }
    _save_portfolio(portfolio)
    _save_trade_log([])
    return portfolio
