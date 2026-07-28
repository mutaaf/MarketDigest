"""Options signal generation — SPY/AAPL with IV awareness and 2:1 R/R enforcement."""

import yaml
from pathlib import Path

import pandas as pd

from src.analysis.technicals import (
    compute_rsi, compute_atr, compute_pivot_points,
    compute_macd, compute_bollinger_bands, detect_ema_crossover,
)
from src.signals.confluence import compute_confluence
from src.signals.models import Signal, PositionSize, OptionDetails
from src.utils.logging_config import get_logger

logger = get_logger("options_signals")

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "signals.yaml"
RISK_PATH = Path(__file__).parent.parent.parent / "config" / "risk.yaml"


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _load_risk() -> dict:
    with open(RISK_PATH) as f:
        return yaml.safe_load(f)


def _compute_iv_rank(df: pd.DataFrame, period: int = 252) -> float | None:
    """Estimate IV rank from historical volatility as proxy.

    Uses realized volatility percentile over the past year.
    Real IV rank requires options chain data (Tastytrade integration).
    """
    if df is None or len(df) < period:
        return None

    close = df["Close"]
    returns = close.pct_change().dropna()
    if len(returns) < period:
        return None

    # 20-day rolling realized vol
    rolling_vol = returns.rolling(20).std() * (252 ** 0.5)
    rolling_vol = rolling_vol.dropna()
    if len(rolling_vol) < 50:
        return None

    current_vol = float(rolling_vol.iloc[-1])
    vol_min = float(rolling_vol.min())
    vol_max = float(rolling_vol.max())

    if vol_max == vol_min:
        return 50.0

    iv_rank = (current_vol - vol_min) / (vol_max - vol_min) * 100
    return round(max(0, min(100, iv_rank)), 1)


def _compute_indicators(df: pd.DataFrame, config: dict) -> dict:
    """Compute all indicators for options signal scoring."""
    if df is None or len(df) < 50:
        return {}

    close = df["Close"]
    params = config.get("indicators", {})

    rsi_series = compute_rsi(close, params.get("rsi_period", 14))
    rsi_val = float(rsi_series.iloc[-1]) if not rsi_series.empty else None

    atr = compute_atr(df, params.get("atr_period", 14))

    prev_high = float(df["High"].iloc[-2]) if len(df) > 1 else None
    prev_low = float(df["Low"].iloc[-2]) if len(df) > 1 else None
    prev_close = float(close.iloc[-2]) if len(close) > 1 else None
    pivots = compute_pivot_points(prev_high, prev_low, prev_close) if prev_high else {}

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

    iv_rank = _compute_iv_rank(df)

    return {
        "rsi": rsi_val,
        "atr": atr,
        "pivots": pivots,
        "macd": macd,
        "bollinger": bb,
        "ema_cross": ema_cross,
        "iv_rank": iv_rank,
    }


def _determine_direction(indicators: dict) -> str:
    """Determine BUY or SELL based on indicator consensus."""
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
            bullish += 1
        elif rsi > 55:
            bearish += 1

    macd = indicators.get("macd")
    if macd:
        if macd.get("histogram", 0) > 0:
            bullish += 1
        else:
            bearish += 1

    bb = indicators.get("bollinger")
    if bb:
        if bb.get("pct_b", 0.5) < 0.3:
            bullish += 1
        elif bb.get("pct_b", 0.5) > 0.7:
            bearish += 1

    return "BUY" if bullish >= bearish else "SELL"


def _select_option_strategy(direction: str, iv_rank: float | None,
                            risk_config: dict) -> str:
    """Select option strategy based on direction and IV."""
    allowed = risk_config.get("allowed_strategies", ["long_call", "long_put"])

    if direction == "BUY":
        if iv_rank and iv_rank < 30 and "long_call" in allowed:
            return "long_call"  # Low IV = buy calls
        if "bull_call_spread" in allowed:
            return "bull_call_spread"  # Defined risk spread
        return "long_call"
    else:
        if iv_rank and iv_rank < 30 and "long_put" in allowed:
            return "long_put"
        if "bear_put_spread" in allowed:
            return "bear_put_spread"
        return "long_put"


def _compute_position_size(dollar_risk: float, risk_config: dict) -> PositionSize:
    """Compute options position size for $500 account."""
    balance = risk_config.get("account_balance", 500.0)
    max_risk_pct = risk_config.get("max_risk_per_trade_pct", 8.0)
    max_dollar_risk = balance * (max_risk_pct / 100)

    actual_risk = min(dollar_risk, max_dollar_risk)
    contracts = max(1, int(max_dollar_risk / max(dollar_risk, 1)))

    return PositionSize(
        units=contracts,
        dollar_risk=round(actual_risk, 2),
        dollar_reward=round(actual_risk * 2, 2),
        label=f"{contracts} contract{'s' if contracts > 1 else ''}",
    )


def _try_direction(direction: str, price: float, indicators: dict,
                   instrument: dict, config: dict, risk_config: dict) -> Signal | None:
    """Try generating an options signal in a specific direction."""
    score, grade, components = compute_confluence(
        price, direction, indicators, asset_type="options"
    )

    min_score = config.get("min_confluence_score", 55)
    if score < min_score:
        return None

    atr = indicators.get("atr") or price * 0.01
    pivots = indicators.get("pivots", {})
    trade_mgmt = config.get("trade_management", {})

    if direction == "BUY":
        s1 = pivots.get("s1", price - atr * 1.5)
        stop = max(s1, price - atr * 1.5) if s1 and s1 < price else price - atr * 1.5
        risk = price - stop
        target_1 = price + risk * trade_mgmt.get("target_1_r", 2.0)
        target_2 = price + risk * trade_mgmt.get("target_2_r", 3.0)
    else:
        r1 = pivots.get("r1", price + atr * 1.5)
        stop = min(r1, price + atr * 1.5) if r1 and r1 > price else price + atr * 1.5
        risk = stop - price
        target_1 = price - risk * trade_mgmt.get("target_1_r", 2.0)
        target_2 = price - risk * trade_mgmt.get("target_2_r", 3.0)

    if risk <= 0:
        return None

    rr = abs(target_1 - price) / risk
    if rr < config.get("min_risk_reward", 2.0):
        return None

    iv_rank = indicators.get("iv_rank")
    strategy = _select_option_strategy(direction, iv_rank, risk_config)

    est_premium = risk * 0.5
    est_premium = max(risk_config.get("min_option_price", 0.50),
                      min(est_premium, risk_config.get("max_option_price", 3.00)))
    pos_size = _compute_position_size(est_premium * 100, risk_config)

    strike = round(price, 0)
    option_details = OptionDetails(
        strategy=strategy, strike=strike, expiry="", dte=14,
        iv=None, delta=0.50 if direction == "BUY" else -0.50,
        theta=None, iv_rank=iv_rank,
    )

    return Signal(
        symbol=instrument["symbol"],
        name=instrument.get("name", instrument["symbol"]),
        asset_type="option",
        direction=direction,
        confluence_score=score, grade=grade,
        entry_price=round(price, 2), stop_loss=round(stop, 2),
        target_1=round(target_1, 2), target_2=round(target_2, 2),
        risk_reward=round(rr, 2), position_size=pos_size,
        indicators={
            "rsi": indicators.get("rsi"), "ema_cross": indicators.get("ema_cross"),
            "macd": indicators.get("macd"), "bollinger": indicators.get("bollinger"),
            "pivots": indicators.get("pivots"), "atr": indicators.get("atr"),
            "iv_rank": iv_rank, "components": components,
        },
        option_details=option_details, pine_strategy="multi_confluence",
    )


def _strategy_signal_to_signal(ss, instrument: dict, risk_config: dict) -> Signal:
    """Convert StrategySignal to Signal model for options."""
    balance = risk_config.get("account_balance", 500.0)
    max_risk_pct = risk_config.get("max_risk_per_trade_pct", 8.0)
    max_dollar_risk = balance * (max_risk_pct / 100)

    from src.analysis.daytrade_scorer import score_to_grade

    return Signal(
        symbol=instrument["symbol"],
        name=instrument.get("name", instrument["symbol"]),
        asset_type="option",
        direction=ss.direction,
        confluence_score=ss.confidence,
        grade=score_to_grade(ss.confidence),
        entry_price=ss.entry_price,
        stop_loss=ss.stop_loss,
        target_1=ss.target_1,
        target_2=ss.target_2,
        risk_reward=ss.risk_reward,
        position_size=PositionSize(
            units=1,
            dollar_risk=round(min(max_dollar_risk, max_dollar_risk), 2),
            dollar_reward=round(max_dollar_risk * max(ss.risk_reward, 1), 2),
            label="1 contract",
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
        option_details=OptionDetails(
            strategy=ss.indicators_used.get("strategy_type", "long_call" if ss.direction == "BUY" else "long_put"),
            strike=round(ss.entry_price, 0),
            expiry="",
            dte=14,
            iv_rank=ss.indicators_used.get("iv_rank"),
            delta=0.50 if ss.direction == "BUY" else -0.50,
        ),
    )


def generate_options_signals(df: pd.DataFrame, instrument: dict) -> list[Signal]:
    """Generate options signals using strategy-based approach.

    Uses market regime detection → strategy selection → specific entry conditions.
    Includes options-specific strategies (IV premium selling, ORB).
    """
    config = _load_config()
    risk_config = _load_risk().get("options", {})

    from src.signals.strategies.selector import select_and_run, compute_all_indicators
    indicators = compute_all_indicators(df, config)
    if not indicators:
        return []

    strategy_signals = select_and_run(df, indicators, instrument, "option")

    signals = [_strategy_signal_to_signal(ss, instrument, risk_config)
               for ss in strategy_signals]

    return signals
