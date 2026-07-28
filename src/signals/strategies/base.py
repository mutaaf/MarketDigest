"""Strategy base classes and data models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd


class MarketRegime(Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_vol"


@dataclass
class TradeTiming:
    hold_duration: str = ""       # e.g. "1-3 days", "1-2 weeks"
    time_horizon: str = ""        # "intraday", "swing", "position"
    best_entry_window: str = ""   # e.g. "US market open (9:30-10:30 ET)", "any"
    time_stop_bars: int = 0       # Auto-close after N bars if no target/stop hit
    urgency: str = ""             # "act now", "wait for pullback", "set limit order"
    when_to_exit: str = ""        # Human-readable exit instructions


@dataclass
class StrategySignal:
    direction: str  # "BUY" or "SELL"
    entry_price: float = 0.0
    stop_loss: float = 0.0
    target_1: float = 0.0
    target_2: float = 0.0
    strategy_name: str = ""
    confidence: float = 0.0  # 0-100, based on conditions met
    regime: MarketRegime = MarketRegime.RANGING
    explanation: str = ""
    conditions_met: list[str] = field(default_factory=list)
    conditions_failed: list[str] = field(default_factory=list)
    indicators_used: dict = field(default_factory=dict)
    risk_reward: float = 0.0
    expected_win_rate: float = 0.0
    timing: TradeTiming = field(default_factory=TradeTiming)

    def compute_rr(self) -> float:
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.target_1 - self.entry_price)
        self.risk_reward = round(reward / risk, 2) if risk > 0 else 0
        return self.risk_reward


class BaseStrategy(ABC):
    name: str = "base"
    description: str = ""
    suitable_regimes: list[MarketRegime] = []
    suitable_assets: list[str] = []  # ["forex", "equity", "option"]
    expected_win_rate: float = 50.0
    expected_rr: float = 2.0

    @abstractmethod
    def check_entry(self, df: pd.DataFrame, indicators: dict,
                    config: dict | None = None) -> StrategySignal | None:
        """Return a StrategySignal if entry conditions are met, else None."""
        ...

    def should_filter(self, df: pd.DataFrame, indicators: dict) -> tuple[bool, str]:
        """Return (True, reason) if this trade should be filtered out.
        Default: no filter. Override in subclasses.
        """
        return False, ""

    def _confidence(self, met: list[str], total: int, bonus: int = 0) -> float:
        """Confidence = % of required conditions met + bonus."""
        if total == 0:
            return 0
        base = (len(met) / total) * 80
        return min(100, base + min(bonus * 5, 20))

    def _build_explanation(self, met: list[str], failed: list[str],
                           direction: str, symbol: str = "") -> str:
        """Build a human-readable explanation of why this strategy fired."""
        parts = [f"{self.name} strategy: {direction} {symbol}."]
        if met:
            parts.append(f"Conditions met: {', '.join(met)}.")
        if failed:
            parts.append(f"Missing: {', '.join(failed)}.")
        return " ".join(parts)
