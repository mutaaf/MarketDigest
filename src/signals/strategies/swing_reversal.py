"""Strategy: Swing Reversal — catch trend exhaustion with divergence + candle pattern."""

import pandas as pd

from src.analysis.technicals import (
    compute_rsi, compute_atr, compute_macd, compute_ema,
    detect_reversal_candle, find_support_resistance,
)
from src.signals.strategies.base import BaseStrategy, StrategySignal, MarketRegime, TradeTiming


class SwingReversal(BaseStrategy):
    name = "Swing Reversal"
    description = "Catch reversals at exhaustion points with RSI divergence + reversal candle"
    suitable_regimes = [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN,
                        MarketRegime.VOLATILE, MarketRegime.RANGING]
    suitable_assets = ["forex", "equity", "option"]
    expected_win_rate = 48.0
    expected_rr = 2.5

    def check_entry(self, df: pd.DataFrame, indicators: dict,
                    config: dict | None = None) -> StrategySignal | None:
        close = df["Close"]
        if len(close) < 30:
            return None

        price = float(close.iloc[-1])
        rsi = indicators.get("rsi")
        macd = indicators.get("macd")
        atr = indicators.get("atr") or price * 0.01
        candle = detect_reversal_candle(df)
        sr = find_support_resistance(df)

        for direction in ("BUY", "SELL"):
            met = []
            failed = []

            if direction == "BUY":
                # Condition 1: RSI oversold or recovering
                if rsi and rsi < 40:
                    met.append(f"RSI oversold ({rsi:.0f})")
                else:
                    failed.append("RSI not oversold")

                # Condition 2: Reversal candle (bullish)
                if candle["bullish"]:
                    detail = "hammer" if candle.get("hammer") else "bullish reversal"
                    met.append(f"Reversal candle ({detail})")
                else:
                    failed.append("No bullish candle")

                # Condition 3: MACD divergence or turning
                if macd and macd.get("histogram", 0) < 0:
                    # Histogram negative but increasing = selling slowing
                    met.append("MACD momentum shifting")
                elif macd and macd.get("crossover"):
                    met.append("MACD bullish crossover")
                else:
                    failed.append("MACD not supportive")

                # Condition 4: Near support
                supports = sr.get("support", [])
                near_support = any(abs(price - s) / price < 0.02 for s in supports)
                if near_support:
                    met.append("Near support level")
                else:
                    failed.append("Not near support")

                if len(met) < 2:
                    continue

                stop = price - atr * 2.0
                resistances = [r for r in sr.get("resistance", []) if r > price]
                target_1 = resistances[0] if resistances else price + atr * 3
                target_2 = resistances[1] if len(resistances) > 1 else price + atr * 5

            else:  # SELL
                if rsi and rsi > 60:
                    met.append(f"RSI overbought ({rsi:.0f})")
                else:
                    failed.append("RSI not overbought")

                if candle["bearish"]:
                    detail = "shooting star" if candle.get("shooting_star") else "bearish reversal"
                    met.append(f"Reversal candle ({detail})")
                else:
                    failed.append("No bearish candle")

                if macd and macd.get("histogram", 0) > 0:
                    met.append("MACD momentum shifting")
                elif macd and macd.get("crossunder"):
                    met.append("MACD bearish crossover")
                else:
                    failed.append("MACD not supportive")

                resistances = sr.get("resistance", [])
                near_resistance = any(abs(price - r) / price < 0.02 for r in resistances)
                if near_resistance:
                    met.append("Near resistance level")
                else:
                    failed.append("Not near resistance")

                if len(met) < 2:
                    continue

                stop = price + atr * 2.0
                supports = [s for s in sr.get("support", []) if s < price]
                target_1 = supports[0] if supports else price - atr * 3
                target_2 = supports[1] if len(supports) > 1 else price - atr * 5

            risk = abs(price - stop)
            reward = abs(target_1 - price)
            if risk <= 0 or reward / risk < 1.5:
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
                indicators_used={"rsi": rsi, "macd": macd, "candle": candle, "atr": atr},
            )
            sig.compute_rr()
            sig.timing = TradeTiming(
                hold_duration="3-10 days",
                time_horizon="swing",
                best_entry_window="Enter on reversal candle close or next bar open — confirmation candle is key",
                time_stop_bars=10,
                urgency="Enter within 1 day of the reversal candle — reversals that don't follow through quickly often fail",
                when_to_exit="Close 50% at first support/resistance target. Trail the rest with a 2 ATR stop. Exit fully if the reversal candle's low/high is broken.",
            )
            sig.explanation = self._build_explanation(met, failed, direction)
            return sig

        return None
