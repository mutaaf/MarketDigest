"""Strategy: Volatility Squeeze — trade the breakout when BB squeezes inside Keltner Channels."""

import pandas as pd

from src.analysis.technicals import (
    compute_bollinger_bands,
)
from src.signals.strategies.base import BaseStrategy, MarketRegime, StrategySignal, TradeTiming


class VolatilitySqueeze(BaseStrategy):
    name = "Volatility Squeeze"
    description = "Trade breakout when BB squeezes — momentum builds then releases (TTM Squeeze)"
    suitable_regimes = [MarketRegime.LOW_VOLATILITY, MarketRegime.RANGING, MarketRegime.VOLATILE]
    suitable_assets = ["forex", "equity", "option"]
    expected_win_rate = 45.0
    expected_rr = 2.5

    def check_entry(self, df: pd.DataFrame, indicators: dict,
                    config: dict | None = None) -> StrategySignal | None:
        close = df["Close"]
        if len(close) < 30:
            return None

        price = float(close.iloc[-1])
        bb = indicators.get("bollinger")
        macd = indicators.get("macd")
        rsi = indicators.get("rsi")
        vol_ratio = indicators.get("volume_ratio")

        if not bb:
            return None

        # Check for squeeze: BB bandwidth in bottom percentile
        is_squeeze = bb.get("squeeze", False) or bb["bandwidth"] < 4.0

        # Check if squeeze is releasing (bandwidth expanding after squeeze)
        # Look at last 5 bars for squeeze
        was_in_squeeze = False
        for i in range(2, min(6, len(close))):
            prev_bb = compute_bollinger_bands(close.iloc[:-i+1] if i > 1 else close, 20, 2.0)
            if prev_bb and prev_bb.get("bandwidth", 10) < bb["bandwidth"]:
                was_in_squeeze = True
                break

        squeeze_releasing = was_in_squeeze and not is_squeeze

        for direction in ("BUY", "SELL"):
            met = []
            failed = []

            if direction == "BUY":
                # Condition 1: Squeeze is releasing or was recent
                if squeeze_releasing:
                    met.append("Squeeze releasing (bandwidth expanding)")
                elif is_squeeze:
                    met.append("In squeeze (awaiting breakout)")
                elif bb["bandwidth"] < 6.0:
                    met.append(f"Low bandwidth ({bb['bandwidth']:.1f}%)")
                else:
                    failed.append("No squeeze detected")

                # Condition 2: Price breaking above middle BB
                if price > bb["middle"]:
                    met.append(f"Price above middle BB ({bb['middle']:.4f})")
                else:
                    failed.append("Price below middle BB")

                # Condition 3: MACD momentum positive
                if macd and macd.get("histogram", 0) > 0:
                    met.append("MACD momentum positive")
                elif macd and macd.get("crossover"):
                    met.append("MACD bullish crossover")
                else:
                    failed.append("MACD not supportive")

                # Condition 4: Volume
                if vol_ratio and vol_ratio >= 1.0:
                    met.append(f"Volume {vol_ratio:.1f}x avg")

                if len(met) < 2:
                    continue

                stop = bb["lower"]
                target_1 = price + (price - bb["lower"]) * 1.5
                target_2 = price + (price - bb["lower"]) * 2.5

            else:  # SELL
                if squeeze_releasing:
                    met.append("Squeeze releasing (bandwidth expanding)")
                elif is_squeeze:
                    met.append("In squeeze (awaiting breakout)")
                elif bb["bandwidth"] < 6.0:
                    met.append(f"Low bandwidth ({bb['bandwidth']:.1f}%)")
                else:
                    failed.append("No squeeze detected")

                if price < bb["middle"]:
                    met.append(f"Price below middle BB ({bb['middle']:.4f})")
                else:
                    failed.append("Price above middle BB")

                if macd and macd.get("histogram", 0) < 0:
                    met.append("MACD momentum negative")
                elif macd and macd.get("crossunder"):
                    met.append("MACD bearish crossunder")
                else:
                    failed.append("MACD not supportive")

                if vol_ratio and vol_ratio >= 1.0:
                    met.append(f"Volume {vol_ratio:.1f}x avg")

                if len(met) < 2:
                    continue

                stop = bb["upper"]
                target_1 = price - (bb["upper"] - price) * 1.5
                target_2 = price - (bb["upper"] - price) * 2.5

            risk = abs(price - stop)
            reward = abs(target_1 - price)
            if risk <= 0 or reward / risk < 1.3:
                continue

            sig = StrategySignal(
                direction=direction,
                entry_price=round(price, 5),
                stop_loss=round(stop, 5),
                target_1=round(target_1, 5),
                target_2=round(target_2, 5),
                strategy_name=self.name,
                confidence=self._confidence(met, 4),
                conditions_met=met,
                conditions_failed=failed,
                expected_win_rate=self.expected_win_rate,
                indicators_used={"bb": bb, "macd": macd, "rsi": rsi,
                                 "vol_ratio": vol_ratio, "squeeze_releasing": squeeze_releasing},
            )
            sig.compute_rr()
            sig.timing = TradeTiming(
                hold_duration="2-7 days (squeezes resolve quickly once they break)",
                time_horizon="swing",
                best_entry_window="Enter on squeeze release candle — when BB expands after compression",
                time_stop_bars=10,
                urgency="Act on the breakout day — squeezes are explosive but short-lived, the first 2-3 bars carry most of the move",
                when_to_exit="Ride the momentum expansion. Close when Bollinger Bandwidth starts contracting again or price re-enters the Bollinger range. Use lower BB as trailing stop for longs.",
            )
            sig.explanation = self._build_explanation(met, failed, direction)
            return sig

        return None
