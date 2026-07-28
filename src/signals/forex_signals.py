"""Forex signal generation — USD/JPY focused with 2:1 R/R enforcement."""

from pathlib import Path

import pandas as pd
import yaml

from src.analysis.technicals import (
    compute_atr,
    compute_bollinger_bands,
    compute_macd,
    compute_pivot_points,
    compute_rsi,
    compute_stochastic,
    detect_ema_crossover,
)
from src.signals.confluence import compute_confluence
from src.signals.models import PositionSize, Signal
from src.utils.logging_config import get_logger

logger = get_logger("forex_signals")

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "signals.yaml"
RISK_PATH = Path(__file__).parent.parent.parent / "config" / "risk.yaml"


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _load_risk() -> dict:
    with open(RISK_PATH) as f:
        return yaml.safe_load(f)


def _compute_all_indicators(df: pd.DataFrame, config: dict) -> dict:
    """Compute all indicators needed for confluence scoring."""
    if df is None or len(df) < 50:
        return {}

    close = df["Close"]
    params = config.get("indicators", {})

    rsi_series = compute_rsi(close, params.get("rsi_period", 14))
    rsi_val = float(rsi_series.iloc[-1]) if not rsi_series.empty else None

    atr = compute_atr(df, params.get("atr_period", 14))

    # Previous day pivots
    prev_high = float(df["High"].iloc[-2]) if len(df) > 1 else None
    prev_low = float(df["Low"].iloc[-2]) if len(df) > 1 else None
    prev_close = float(close.iloc[-2]) if len(close) > 1 else None
    pivots = compute_pivot_points(prev_high, prev_low, prev_close) if prev_high else {}

    stoch = compute_stochastic(
        df, params.get("stoch_k", 14),
        params.get("stoch_d", 3), params.get("stoch_smooth", 3)
    )

    macd = compute_macd(
        close, params.get("macd_fast", 12),
        params.get("macd_slow", 26), params.get("macd_signal", 9)
    )

    bb = compute_bollinger_bands(
        close, params.get("bb_period", 20), params.get("bb_std", 2.0)
    )

    ema_cross = detect_ema_crossover(
        close, params.get("ema_fast", 9), params.get("ema_slow", 21)
    )

    return {
        "rsi": rsi_val,
        "atr": atr,
        "pivots": pivots,
        "stochastic": stoch,
        "macd": macd,
        "bollinger": bb,
        "ema_cross": ema_cross,
    }


def _determine_direction(indicators: dict) -> str:
    """Determine BUY or SELL based on indicator alignment."""
    bullish = 0
    bearish = 0

    ema = indicators.get("ema_cross", {})
    if ema.get("signal") in ("bullish_cross", "bullish"):
        bullish += 2
    elif ema.get("signal") in ("bearish_cross", "bearish"):
        bearish += 2

    rsi = indicators.get("rsi")
    if rsi is not None:
        if rsi < 45:
            bullish += 1  # Recovery zone
        elif rsi > 55:
            bearish += 1

    macd = indicators.get("macd")
    if macd:
        if macd.get("histogram", 0) > 0:
            bullish += 1
        else:
            bearish += 1

    stoch = indicators.get("stochastic")
    if stoch:
        if stoch.get("k", 50) < 30:
            bullish += 1
        elif stoch.get("k", 50) > 70:
            bearish += 1

    bb = indicators.get("bollinger")
    if bb:
        if bb.get("pct_b", 0.5) < 0.3:
            bullish += 1
        elif bb.get("pct_b", 0.5) > 0.7:
            bearish += 1

    if bullish > bearish:
        return "BUY"
    elif bearish > bullish:
        return "SELL"
    return "BUY" if bullish >= bearish else "SELL"


def _compute_levels(price: float, direction: str, indicators: dict,
                    config: dict) -> tuple[float, float, float, float]:
    """Compute entry, stop, target_1 (2R), target_2 (3R).

    Returns (entry, stop, target_1, target_2) or raises ValueError if R/R < 2.0.
    """
    atr = indicators.get("atr") or price * 0.01
    pivots = indicators.get("pivots", {})
    stop_mult = 1.5  # ATR multiplier for stops

    trade_mgmt = config.get("trade_management", {})
    t1_r = trade_mgmt.get("target_1_r", 2.0)
    t2_r = trade_mgmt.get("target_2_r", 3.0)

    entry = price

    if direction == "BUY":
        # Stop below S1 or ATR-based, whichever is tighter but still valid
        s1 = pivots.get("s1")
        atr_stop = price - atr * stop_mult
        if s1 and s1 < price:
            stop = max(s1, atr_stop)  # Use closer stop
        else:
            stop = atr_stop

        risk = entry - stop
        if risk <= 0:
            raise ValueError("Invalid stop: stop >= entry")

        target_1 = entry + risk * t1_r
        target_2 = entry + risk * t2_r

    else:  # SELL
        r1 = pivots.get("r1")
        atr_stop = price + atr * stop_mult
        if r1 and r1 > price:
            stop = min(r1, atr_stop)
        else:
            stop = atr_stop

        risk = stop - entry
        if risk <= 0:
            raise ValueError("Invalid stop: stop <= entry")

        target_1 = entry - risk * t1_r
        target_2 = entry - risk * t2_r

    return round(entry, 5), round(stop, 5), round(target_1, 5), round(target_2, 5)


def _compute_position_size(entry: float, stop: float, instrument: dict,
                           risk_config: dict) -> PositionSize:
    """Compute position size for forex based on $500 account."""
    balance = risk_config.get("account_balance", 500.0)
    max_risk_pct = risk_config.get("max_risk_per_trade_pct", 2.0)
    max_dollar_risk = balance * (max_risk_pct / 100)

    pip_size = instrument.get("pip_size", 0.01)
    pip_value = instrument.get("pip_value_per_micro_lot", 0.07)

    stop_distance = abs(entry - stop)
    stop_pips = stop_distance / pip_size

    if stop_pips <= 0 or pip_value <= 0:
        return PositionSize(units=1, dollar_risk=max_dollar_risk,
                            dollar_reward=max_dollar_risk * 2, label="1 micro lot")

    lots = max_dollar_risk / (stop_pips * pip_value)
    lots = max(1, int(lots))  # At least 1 micro lot

    actual_risk = lots * stop_pips * pip_value
    actual_reward = actual_risk * 2  # 2:1 minimum

    return PositionSize(
        units=lots,
        dollar_risk=round(actual_risk, 2),
        dollar_reward=round(actual_reward, 2),
        label=f"{lots} micro lot{'s' if lots > 1 else ''}",
    )


def _try_direction(direction: str, price: float, indicators: dict,
                   instrument: dict, config: dict, risk_config: dict) -> Signal | None:
    """Try generating a signal in a specific direction. Returns None if invalid."""
    score, grade, components = compute_confluence(
        price, direction, indicators, asset_type="forex"
    )

    min_score = config.get("min_confluence_score", 55)
    if score < min_score:
        return None

    try:
        entry, stop, target_1, target_2 = _compute_levels(
            price, direction, indicators, config
        )
    except ValueError:
        return None

    risk = abs(entry - stop)
    reward = abs(target_1 - entry)
    rr = reward / risk if risk > 0 else 0

    min_rr = config.get("min_risk_reward", 2.0)
    if rr < min_rr:
        return None

    pos_size = _compute_position_size(entry, stop, instrument, risk_config)

    return Signal(
        symbol=instrument["symbol"],
        name=instrument.get("name", instrument["symbol"]),
        asset_type="forex",
        direction=direction,
        confluence_score=score,
        grade=grade,
        entry_price=entry,
        stop_loss=stop,
        target_1=target_1,
        target_2=target_2,
        risk_reward=round(rr, 2),
        position_size=pos_size,
        indicators={
            "rsi": indicators.get("rsi"),
            "ema_cross": indicators.get("ema_cross"),
            "stochastic": indicators.get("stochastic"),
            "macd": indicators.get("macd"),
            "bollinger": indicators.get("bollinger"),
            "pivots": indicators.get("pivots"),
            "atr": indicators.get("atr"),
            "components": components,
        },
        pine_strategy="ema_crossover",
    )


def _strategy_signal_to_signal(ss, instrument: dict, risk_config: dict) -> Signal:
    """Convert a StrategySignal to a Signal model."""
    from src.signals.models import PositionSize

    balance = risk_config.get("account_balance", 500.0)
    max_risk_pct = risk_config.get("max_risk_per_trade_pct", 2.0)
    max_dollar_risk = balance * (max_risk_pct / 100)

    pip_size = instrument.get("pip_size", 0.01)
    pip_value = instrument.get("pip_value_per_micro_lot", 0.07)
    risk_distance = abs(ss.entry_price - ss.stop_loss)
    stop_pips = risk_distance / pip_size if pip_size > 0 else 1

    if stop_pips > 0 and pip_value > 0:
        lots = max(1, int(max_dollar_risk / (stop_pips * pip_value)))
        actual_risk = lots * stop_pips * pip_value
    else:
        lots = 1
        actual_risk = max_dollar_risk

    actual_risk = min(actual_risk, max_dollar_risk)
    actual_reward = actual_risk * ss.risk_reward

    return Signal(
        symbol=instrument["symbol"],
        name=instrument.get("name", instrument["symbol"]),
        asset_type="forex",
        direction=ss.direction,
        confluence_score=ss.confidence,
        grade=_score_to_grade(ss.confidence),
        entry_price=ss.entry_price,
        stop_loss=ss.stop_loss,
        target_1=ss.target_1,
        target_2=ss.target_2,
        risk_reward=ss.risk_reward,
        position_size=PositionSize(
            units=lots, dollar_risk=round(actual_risk, 2),
            dollar_reward=round(actual_reward, 2),
            label=f"{lots} micro lot{'s' if lots > 1 else ''}",
        ),
        indicators=ss.indicators_used,
        strategy_name=ss.strategy_name,
        regime=ss.regime.value if hasattr(ss.regime, 'value') else str(ss.regime),
        conditions_met=ss.conditions_met,
        explanation=ss.explanation,
        timing={
            "hold_duration": ss.timing.hold_duration,
            "time_horizon": ss.timing.time_horizon,
            "best_entry_window": ss.timing.best_entry_window,
            "time_stop_bars": ss.timing.time_stop_bars,
            "urgency": ss.timing.urgency,
            "when_to_exit": ss.timing.when_to_exit,
        } if ss.timing and ss.timing.hold_duration else None,
    )


def _score_to_grade(score: float) -> str:
    from src.analysis.daytrade_scorer import score_to_grade
    return score_to_grade(score)


def generate_forex_signals(df: pd.DataFrame, instrument: dict) -> list[Signal]:
    """Generate forex signals using strategy-based approach.

    Uses market regime detection → strategy selection → specific entry conditions.
    Only generates signals when ALL conditions of a proven strategy are met.
    """
    config = _load_config()
    risk_config = _load_risk().get("forex", {})

    # Use new strategy engine
    from src.signals.strategies.selector import compute_all_indicators, select_and_run
    indicators = compute_all_indicators(df, config)
    if not indicators:
        return []

    strategy_signals = select_and_run(df, indicators, instrument, "forex")

    # Convert to Signal models
    signals = [_strategy_signal_to_signal(ss, instrument, risk_config)
               for ss in strategy_signals]

    return signals
