"""Learner — analyzes trade outcomes to build rolling strategy performance metrics."""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from src.utils.logging_config import get_logger

logger = get_logger("innovation.learner")

PAPER_LOG = Path(__file__).parent.parent.parent / "logs" / "paper_trades.json"
SIGNALS_DIR = Path(__file__).parent.parent.parent / "logs" / "signals"
PERF_PATH = Path(__file__).parent.parent.parent / "logs" / "innovation" / "performance.json"


def _load_paper_trades() -> list[dict]:
    if PAPER_LOG.exists():
        try:
            with open(PAPER_LOG) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _load_signal_history(days: int = 60) -> dict:
    """Load signal history keyed by signal_id."""
    cutoff = datetime.now() - timedelta(days=days)
    by_id = {}
    if not SIGNALS_DIR.exists():
        return by_id
    for fp in sorted(SIGNALS_DIR.glob("*.json"), reverse=True):
        try:
            date_str = fp.stem.split("_")[0]
            if datetime.strptime(date_str, "%Y-%m-%d") < cutoff:
                break
            with open(fp) as f:
                data = json.load(f)
            for sig in data.get("signals", []):
                sig_id = sig.get("id", "")
                if sig_id:
                    by_id[sig_id] = sig
        except Exception:
            continue
    return by_id


def _load_performance() -> dict:
    if PERF_PATH.exists():
        try:
            with open(PERF_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"updated": None, "strategies": {}, "overall": {}}


def _save_performance(perf: dict):
    PERF_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PERF_PATH, "w") as f:
        json.dump(perf, f, indent=2, default=str)


def collect_trade_outcomes(days: int = 30) -> list[dict]:
    """Collect closed paper trades with matched signal data."""
    trades = _load_paper_trades()
    signals = _load_signal_history(days)
    cutoff = datetime.now() - timedelta(days=days)

    outcomes = []
    for trade in trades:
        if trade.get("event") != "exit":
            continue
        try:
            exit_time = datetime.fromisoformat(trade["exit_time"])
            if exit_time < cutoff:
                continue
        except (KeyError, ValueError):
            continue

        # Match to signal for strategy info
        sig_id = trade.get("signal_id", trade.get("id", ""))
        signal = signals.get(sig_id, {})

        outcomes.append({
            "symbol": trade.get("symbol", ""),
            "direction": trade.get("direction", ""),
            "asset_type": trade.get("asset_type", ""),
            "entry_price": trade.get("entry_price", 0),
            "exit_price": trade.get("exit_price", 0),
            "pnl": trade.get("pnl", 0),
            "r_multiple": trade.get("r_multiple", 0),
            "outcome": trade.get("outcome", ""),
            "exit_reason": trade.get("exit_reason", ""),
            "entry_time": trade.get("entry_time", ""),
            "exit_time": trade.get("exit_time", ""),
            # From matched signal
            "strategy_name": signal.get("strategy_name", trade.get("strategy_name", "unknown")),
            "regime": signal.get("regime", ""),
            "confluence_score": signal.get("confluence_score", 0),
            "grade": signal.get("grade", ""),
            "conditions_met": signal.get("conditions_met", []),
            "indicators": signal.get("indicators", {}),
        })

    return outcomes


def compute_strategy_performance(days: int = 30) -> dict:
    """Compute per-strategy performance metrics.

    Returns dict keyed by strategy_name with:
        total_trades, wins, losses, win_rate, avg_r, total_pnl,
        profit_factor, by_regime, by_asset, best_symbol, worst_symbol
    """
    outcomes = collect_trade_outcomes(days)
    if not outcomes:
        return {}

    by_strategy = defaultdict(list)
    for o in outcomes:
        by_strategy[o["strategy_name"]].append(o)

    results = {}
    for strat_name, trades in by_strategy.items():
        wins = [t for t in trades if t["outcome"] == "win"]
        losses = [t for t in trades if t["outcome"] == "loss"]
        total = len(trades)
        win_rate = len(wins) / total * 100 if total > 0 else 0
        avg_r = sum(t["r_multiple"] for t in trades) / total if total > 0 else 0
        total_pnl = sum(t["pnl"] for t in trades)
        gross_wins = sum(t["pnl"] for t in wins)
        gross_losses = abs(sum(t["pnl"] for t in losses))
        profit_factor = gross_wins / gross_losses if gross_losses > 0 else float("inf")

        # By regime
        by_regime = defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0})
        for t in trades:
            r = t.get("regime", "unknown")
            by_regime[r]["trades"] += 1
            if t["outcome"] == "win":
                by_regime[r]["wins"] += 1
            by_regime[r]["pnl"] += t["pnl"]

        # By symbol
        by_symbol = defaultdict(lambda: {"trades": 0, "pnl": 0})
        for t in trades:
            by_symbol[t["symbol"]]["trades"] += 1
            by_symbol[t["symbol"]]["pnl"] += t["pnl"]

        best_symbol = max(by_symbol.items(), key=lambda x: x[1]["pnl"])[0] if by_symbol else ""
        worst_symbol = min(by_symbol.items(), key=lambda x: x[1]["pnl"])[0] if by_symbol else ""

        results[strat_name] = {
            "total_trades": total,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 1),
            "avg_r": round(avg_r, 2),
            "total_pnl": round(total_pnl, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else "inf",
            "by_regime": dict(by_regime),
            "best_symbol": best_symbol,
            "worst_symbol": worst_symbol,
        }

    return results


def identify_performers(performance: dict) -> dict:
    """Identify outperformers and underperformers.

    Returns {outperformers: [...], underperformers: [...], neutral: [...]}
    """
    # Expected performance per strategy (from BaseStrategy classes)
    expected = {
        "EMA Trend Follow": {"wr": 42, "rr": 2.5},
        "BB Mean Reversion": {"wr": 62, "rr": 1.3},
        "Donchian Breakout": {"wr": 38, "rr": 3.0},
        "RSI Momentum": {"wr": 57, "rr": 1.5},
        "Pivot Bounce": {"wr": 52, "rr": 2.0},
        "IV Premium Sell": {"wr": 72, "rr": 0.5},
        "Range Breakout": {"wr": 47, "rr": 2.0},
        "Swing Reversal": {"wr": 48, "rr": 2.5},
        "MACD Divergence": {"wr": 50, "rr": 2.0},
        "Volatility Squeeze": {"wr": 45, "rr": 2.5},
    }

    out, under, neutral = [], [], []

    for strat_name, metrics in performance.items():
        if metrics["total_trades"] < 5:
            neutral.append({"strategy": strat_name, "reason": "insufficient trades", **metrics})
            continue

        exp = expected.get(strat_name, {"wr": 50, "rr": 2.0})
        wr_diff = metrics["win_rate"] - exp["wr"]

        if wr_diff > 10:
            out.append({"strategy": strat_name, "reason": f"WR {wr_diff:+.0f}% vs expected", **metrics})
        elif wr_diff < -10:
            under.append({"strategy": strat_name, "reason": f"WR {wr_diff:+.0f}% vs expected", **metrics})
        elif metrics["total_pnl"] < 0:
            under.append({"strategy": strat_name, "reason": f"negative P&L (${metrics['total_pnl']:.2f})", **metrics})
        else:
            neutral.append({"strategy": strat_name, **metrics})

    return {"outperformers": out, "underperformers": under, "neutral": neutral}


def update_performance_ledger() -> dict:
    """Run the full learning cycle: collect outcomes, compute metrics, save.

    Returns the performance data.
    """
    perf_30d = compute_strategy_performance(days=30)
    perf_all = compute_strategy_performance(days=365)
    performers = identify_performers(perf_30d)

    # Overall stats
    all_trades = collect_trade_outcomes(days=30)
    total_pnl = sum(t["pnl"] for t in all_trades)
    total_trades = len(all_trades)
    wins = len([t for t in all_trades if t["outcome"] == "win"])

    data = {
        "updated": datetime.now().isoformat(),
        "strategies_30d": perf_30d,
        "strategies_all": perf_all,
        "performers": performers,
        "overall": {
            "total_trades_30d": total_trades,
            "total_pnl_30d": round(total_pnl, 2),
            "win_rate_30d": round(wins / total_trades * 100, 1) if total_trades > 0 else 0,
        },
    }

    _save_performance(data)
    logger.info(f"Performance ledger updated: {total_trades} trades, ${total_pnl:.2f} P&L")
    return data


def get_performance() -> dict:
    """Get latest performance data."""
    return _load_performance()
