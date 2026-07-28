"""Signal data models."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class PositionSize:
    units: float  # Micro lots for forex, contracts for options
    dollar_risk: float
    dollar_reward: float
    label: str  # e.g. "2 micro lots" or "1 contract"


@dataclass
class OptionDetails:
    strategy: str  # long_call, long_put, bull_call_spread, bear_put_spread
    strike: float
    expiry: str  # YYYY-MM-DD
    dte: int
    iv: float | None = None
    delta: float | None = None
    theta: float | None = None
    iv_rank: float | None = None


@dataclass
class Signal:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.now)
    symbol: str = ""
    name: str = ""
    asset_type: Literal["forex", "equity", "option"] = "forex"
    direction: Literal["BUY", "SELL"] = "BUY"
    confluence_score: float = 0.0
    grade: str = "F"
    entry_price: float = 0.0
    stop_loss: float = 0.0
    target_1: float = 0.0  # 2R target
    target_2: float = 0.0  # 3R target
    risk_reward: float = 0.0
    position_size: PositionSize | None = None
    indicators: dict = field(default_factory=dict)
    explanation: str = ""
    pine_strategy: str | None = None
    option_details: OptionDetails | None = None
    strategy_name: str = ""
    regime: str = ""
    conditions_met: list[str] | None = None
    timing: dict | None = None  # hold_duration, time_horizon, urgency, when_to_exit, etc.
    status: Literal["active", "hit_target_1", "hit_target_2",
                     "stopped_out", "breakeven", "expired", "cancelled"] = "active"

    @property
    def dollar_risk(self) -> float:
        return self.position_size.dollar_risk if self.position_size else 0.0

    @property
    def dollar_reward(self) -> float:
        return self.position_size.dollar_reward if self.position_size else 0.0

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "name": self.name,
            "asset_type": self.asset_type,
            "direction": self.direction,
            "confluence_score": self.confluence_score,
            "grade": self.grade,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "target_1": self.target_1,
            "target_2": self.target_2,
            "risk_reward": self.risk_reward,
            "indicators": self.indicators,
            "explanation": self.explanation,
            "pine_strategy": self.pine_strategy,
            "strategy_name": self.strategy_name,
            "regime": self.regime,
            "conditions_met": self.conditions_met,
            "timing": self.timing,
            "status": self.status,
        }
        if self.position_size:
            d["position_size"] = {
                "units": self.position_size.units,
                "dollar_risk": self.position_size.dollar_risk,
                "dollar_reward": self.position_size.dollar_reward,
                "label": self.position_size.label,
            }
        if self.option_details:
            d["option_details"] = {
                "strategy": self.option_details.strategy,
                "strike": self.option_details.strike,
                "expiry": self.option_details.expiry,
                "dte": self.option_details.dte,
                "iv": self.option_details.iv,
                "delta": self.option_details.delta,
                "theta": self.option_details.theta,
                "iv_rank": self.option_details.iv_rank,
            }
        return d
