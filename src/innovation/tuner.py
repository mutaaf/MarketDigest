"""Tuner — parameter optimization via hill-climbing with backtest validation."""

from pathlib import Path

import yaml

from src.innovation.config_manager import safe_update_strategy_param
from src.innovation.learner import compute_strategy_performance
from src.innovation.safety import (
    check_daily_budget,
    is_auto_tune,
    load_innovation_config,
)
from src.utils.logging_config import get_logger

logger = get_logger("innovation.tuner")

SIGNALS_YAML = Path(__file__).parent.parent.parent / "config" / "signals.yaml"


def _load_signals_config() -> dict:
    with open(SIGNALS_YAML) as f:
        return yaml.safe_load(f)


def _get_strategy_ticker(strategy_name: str) -> tuple[str, str]:
    """Get a representative ticker for backtesting a strategy."""
    # Map strategy types to good test instruments
    config = _load_signals_config()
    forex = config.get("signal_instruments", {}).get("forex", [])
    options = config.get("signal_instruments", {}).get("options", [])

    forex_map = {
        "ema_trend_follow": forex[0] if forex else None,
        "bollinger_mean_reversion": forex[0] if forex else None,
        "donchian_breakout": forex[0] if forex else None,
        "pivot_bounce": forex[0] if forex else None,
        "swing_reversal": forex[0] if forex else None,
        "macd_divergence": forex[0] if forex else None,
        "volatility_squeeze": forex[0] if forex else None,
    }
    options_map = {
        "rsi_momentum": options[0] if options else None,
        "iv_premium": options[0] if options else None,
        "orb_breakout": options[0] if options else None,
    }

    inst = forex_map.get(strategy_name) or options_map.get(strategy_name)
    if inst:
        return inst.get("yfinance", "SPY"), "forex" if strategy_name in forex_map else "options"
    return "SPY", "options"


def hill_climb_strategy(strategy_name: str) -> list[dict]:
    """Run hill-climbing on a strategy's tunable parameters.

    Tests current value +/- step for each parameter.
    Returns list of proposals: {param, old, new, improvement, reason}
    """
    from src.signals.engine import backtest_strategy

    innov_cfg = load_innovation_config()
    bounds = innov_cfg.get("tunable_parameters", {}).get(strategy_name, {})
    if not bounds:
        return []

    signals_cfg = _load_signals_config()
    strat_config = signals_cfg.get("strategies", {}).get(strategy_name, {})

    ticker, asset_type = _get_strategy_ticker(strategy_name)
    proposals = []

    # Baseline backtest
    try:
        baseline = backtest_strategy(ticker, asset_type=asset_type, lookback_months=3, start_balance=500)
        baseline_fitness = _compute_fitness(baseline)
    except Exception as e:
        logger.warning(f"Baseline backtest failed for {strategy_name}: {e}")
        return []

    for param, param_bounds in bounds.items():
        current = strat_config.get(param)
        if current is None:
            continue

        step = param_bounds.get("step", 1)
        test_values = []

        # Test current - step
        down = round(current - step, 4)
        if down >= param_bounds["min"]:
            test_values.append(down)

        # Test current + step
        up = round(current + step, 4)
        if up <= param_bounds["max"]:
            test_values.append(up)

        for test_val in test_values:
            # Temporarily modify config for backtest
            signals_cfg["strategies"][strategy_name][param] = test_val
            try:
                result = backtest_strategy(ticker, asset_type=asset_type, lookback_months=3, start_balance=500)
                fitness = _compute_fitness(result)

                improvement = fitness - baseline_fitness
                if improvement > 0.05:  # At least 5% improvement
                    proposals.append({
                        "strategy": strategy_name,
                        "param": param,
                        "old_value": current,
                        "new_value": test_val,
                        "improvement_pct": round(improvement * 100, 1),
                        "reason": _explain_improvement(param, current, test_val, baseline, result),
                        "backtest": {
                            "win_rate": result.get("win_rate", 0),
                            "profit_factor": result.get("profit_factor", 0),
                            "total_trades": result.get("total_trades", 0),
                            "total_return_pct": result.get("total_return_pct", 0),
                        },
                    })
            except Exception:
                pass

            # Restore original
            signals_cfg["strategies"][strategy_name][param] = current

    # Sort by improvement
    proposals.sort(key=lambda p: p["improvement_pct"], reverse=True)
    return proposals


def _compute_fitness(backtest_result: dict) -> float:
    """Composite fitness score from backtest results."""
    wr = backtest_result.get("win_rate", 0) / 100
    pf = backtest_result.get("profit_factor", 0)
    if isinstance(pf, str):
        pf = 3.0  # inf
    pf = min(pf, 5.0)  # Cap
    avg_r = backtest_result.get("avg_r_multiple", 0)
    total = backtest_result.get("total_trades", 0)

    if total < 5:
        return 0  # Not enough data

    # 40% profit factor + 30% win rate + 20% avg R + 10% trade count
    trade_score = min(total / 50, 1.0)
    return 0.4 * (pf / 3.0) + 0.3 * wr + 0.2 * max(avg_r / 3.0, 0) + 0.1 * trade_score


def _explain_improvement(param: str, old: float, new: float,
                         baseline: dict, improved: dict) -> str:
    """Generate human-readable explanation for a parameter change."""
    wr_change = improved.get("win_rate", 0) - baseline.get("win_rate", 0)
    pf_old = baseline.get("profit_factor", 0)
    pf_new = improved.get("profit_factor", 0)
    ret_change = improved.get("total_return_pct", 0) - baseline.get("total_return_pct", 0)

    parts = [f"{param}: {old} → {new}"]
    if abs(wr_change) > 1:
        parts.append(f"WR {wr_change:+.1f}%")
    if isinstance(pf_new, (int, float)) and isinstance(pf_old, (int, float)):
        parts.append(f"PF {pf_old:.1f} → {pf_new:.1f}")
    if abs(ret_change) > 1:
        parts.append(f"return {ret_change:+.1f}%")

    return " | ".join(parts)


def propose_and_apply(strategies_to_tune: list[str] | None = None) -> list[dict]:
    """Run full tuning cycle: hill-climb each strategy, apply improvements.

    Returns list of applied changes.
    """
    if not is_auto_tune():
        logger.info("Tuner: not in auto-tune mode, skipping")
        return []

    daily_ok, daily_remaining = check_daily_budget()
    if not daily_ok:
        logger.info("Tuner: daily change budget exhausted")
        return []

    # Determine which strategies to tune (default: those with enough trades)
    perf = compute_strategy_performance(days=30)
    innov_cfg = load_innovation_config()
    min_trades = innov_cfg.get("rate_limits", {}).get("min_trades_for_tuning", 10)

    if strategies_to_tune is None:
        strategies_to_tune = [
            _strategy_name_to_config_key(name)
            for name, metrics in perf.items()
            if metrics.get("total_trades", 0) >= min_trades
        ]

    applied = []
    for strategy_key in strategies_to_tune:
        if daily_remaining <= 0:
            break

        proposals = hill_climb_strategy(strategy_key)
        if not proposals:
            continue

        # Apply the best proposal
        best = proposals[0]
        result = safe_update_strategy_param(
            best["strategy"], best["param"], best["new_value"],
            best["reason"], best.get("backtest"),
        )
        if result.get("success"):
            applied.append({**best, "applied": True})
            daily_remaining -= 1
            logger.info(f"Tuner applied: {best['strategy']}.{best['param']}: "
                        f"{best['old_value']} → {best['new_value']} ({best['reason']})")
        else:
            logger.info(f"Tuner blocked: {result.get('message')}")

    return applied


def _strategy_name_to_config_key(name: str) -> str:
    """Convert display name to config key."""
    mapping = {
        "EMA Trend Follow": "ema_trend_follow",
        "BB Mean Reversion": "bollinger_mean_reversion",
        "Donchian Breakout": "donchian_breakout",
        "RSI Momentum": "rsi_momentum",
        "Pivot Bounce": "pivot_bounce",
        "IV Premium Sell": "iv_premium",
        "Range Breakout": "orb_breakout",
        "Swing Reversal": "swing_reversal",
        "MACD Divergence": "macd_divergence",
        "Volatility Squeeze": "volatility_squeeze",
    }
    return mapping.get(name, name.lower().replace(" ", "_"))
