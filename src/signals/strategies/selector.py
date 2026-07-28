"""Strategy selector — picks the right strategies based on market regime."""

from pathlib import Path

import pandas as pd
import yaml

from src.analysis.technicals import (
    compute_adx,
    compute_atr,
    compute_bollinger_bands,
    compute_macd,
    compute_pivot_points,
    compute_rsi,
    compute_stochastic,
    compute_volume_ratio,
    detect_ema_crossover,
)
from src.signals.strategies.base import MarketRegime, StrategySignal
from src.signals.strategies.breakout import DonchianBreakout
from src.signals.strategies.iv_premium import IVPremiumSelling
from src.signals.strategies.macd_divergence import MACDDivergence
from src.signals.strategies.mean_reversion import BollingerMeanReversion
from src.signals.strategies.momentum import RSIMomentum
from src.signals.strategies.orb import ORBDirectional
from src.signals.strategies.pivot_bounce import PivotBounce
from src.signals.strategies.regime import detect_regime
from src.signals.strategies.swing_reversal import SwingReversal
from src.signals.strategies.trend_ema import EMATrendFollow
from src.signals.strategies.volatility_squeeze import VolatilitySqueeze
from src.utils.logging_config import get_logger

logger = get_logger("strategy_selector")

CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "signals.yaml"

# Strategy registry: which strategies to try for each regime
# Each regime now has 4-6 strategies to maximize signal generation
STRATEGY_REGISTRY = {
    MarketRegime.TRENDING_UP: [
        EMATrendFollow, RSIMomentum, PivotBounce,
        MACDDivergence, SwingReversal,
    ],
    MarketRegime.TRENDING_DOWN: [
        EMATrendFollow, RSIMomentum,
        MACDDivergence, SwingReversal,
    ],
    MarketRegime.RANGING: [
        BollingerMeanReversion, PivotBounce,
        MACDDivergence, SwingReversal, VolatilitySqueeze,
    ],
    MarketRegime.VOLATILE: [
        DonchianBreakout, RSIMomentum,
        SwingReversal, MACDDivergence, VolatilitySqueeze,
    ],
    MarketRegime.LOW_VOLATILITY: [
        DonchianBreakout, VolatilitySqueeze,
        BollingerMeanReversion, MACDDivergence,
    ],
}

# Options-specific strategies (always checked for option assets)
OPTIONS_STRATEGIES = [IVPremiumSelling, ORBDirectional]


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _compute_iv_rank(df: pd.DataFrame, period: int = 252) -> float | None:
    """Estimate IV rank from historical volatility percentile."""
    if df is None or len(df) < period:
        return None
    close = df["Close"]
    returns = close.pct_change().dropna()
    if len(returns) < period:
        return None

    rolling_vol = returns.rolling(20).std() * (252 ** 0.5)
    rolling_vol = rolling_vol.dropna()
    if len(rolling_vol) < 50:
        return None

    current = float(rolling_vol.iloc[-1])
    vol_min = float(rolling_vol.min())
    vol_max = float(rolling_vol.max())

    if vol_max == vol_min:
        return 50.0
    return round(max(0, min(100, (current - vol_min) / (vol_max - vol_min) * 100)), 1)


def compute_all_indicators(df: pd.DataFrame, config: dict | None = None) -> dict:
    """Compute all indicators needed by all strategies."""
    if df is None or len(df) < 50:
        return {}

    cfg = config or _load_config()
    params = cfg.get("indicators", {})
    close = df["Close"]

    rsi_series = compute_rsi(close, params.get("rsi_period", 14))
    rsi_val = float(rsi_series.iloc[-1]) if not rsi_series.empty else None

    atr = compute_atr(df, params.get("atr_period", 14))
    adx = compute_adx(df, 14)

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

    volume_ratio = compute_volume_ratio(df)

    iv_rank = _compute_iv_rank(df)

    return {
        "rsi": rsi_val,
        "atr": atr,
        "adx": adx,
        "pivots": pivots,
        "stochastic": stoch,
        "macd": macd,
        "bollinger": bb,
        "ema_cross": ema_cross,
        "volume_ratio": volume_ratio,
        "iv_rank": iv_rank,
    }


def select_and_run(df: pd.DataFrame, indicators: dict,
                   instrument: dict, asset_type: str) -> list[StrategySignal]:
    """Run all applicable strategies for the current market regime.

    Returns list of StrategySignals sorted by confidence (best first).
    Empty list = no trade (valid outcome).
    """
    config = _load_config()
    regime_config = config.get("regime", {})
    strategy_configs = config.get("strategies", {})

    # Detect market regime
    regime = detect_regime(df, regime_config)

    # Get candidate strategies for this regime
    candidates = STRATEGY_REGISTRY.get(regime, [])

    # Filter to strategies that support this asset type
    candidates = [S for S in candidates if asset_type in S.suitable_assets]

    # Add options-specific strategies
    if asset_type == "option":
        candidates += OPTIONS_STRATEGIES

    # Check which strategies are enabled in config
    enabled_candidates = []
    for StrategyClass in candidates:
        # Map class to config key
        config_key_map = {
            "EMATrendFollow": "ema_trend_follow",
            "BollingerMeanReversion": "bollinger_mean_reversion",
            "DonchianBreakout": "donchian_breakout",
            "RSIMomentum": "rsi_momentum",
            "PivotBounce": "pivot_bounce",
            "IVPremiumSelling": "iv_premium",
            "ORBDirectional": "orb_breakout",
            "SwingReversal": "swing_reversal",
            "MACDDivergence": "macd_divergence",
            "VolatilitySqueeze": "volatility_squeeze",
        }
        config_key = config_key_map.get(StrategyClass.__name__, "")
        strat_config = strategy_configs.get(config_key, {})

        if strat_config.get("enabled", True):
            enabled_candidates.append((StrategyClass, strat_config))

    # Run each strategy
    signals = []
    for StrategyClass, strat_config in enabled_candidates:
        strategy = StrategyClass()

        # Check filter
        filtered, reason = strategy.should_filter(df, indicators)
        if filtered:
            logger.debug(f"{instrument.get('symbol', '?')}: {strategy.name} filtered — {reason}")
            continue

        # Check entry
        signal = strategy.check_entry(df, indicators, config=strat_config)
        if signal:
            signal.regime = regime
            logger.info(f"{instrument.get('symbol', '?')}: {strategy.name} → "
                        f"{signal.direction} (confidence={signal.confidence:.0f}, "
                        f"R/R={signal.risk_reward})")
            signals.append(signal)

    # Sort by confidence descending
    signals.sort(key=lambda s: s.confidence, reverse=True)

    if not signals:
        logger.debug(f"{instrument.get('symbol', '?')}: No strategy fired in {regime.value} regime")

    return signals
