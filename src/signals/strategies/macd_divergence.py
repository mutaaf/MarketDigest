"""Strategy: MACD Divergence — trade divergence between price and MACD histogram."""

import pandas as pd
import numpy as np

from src.analysis.technicals import (
    compute_rsi, compute_atr, compute_macd, compute_ema,
    find_support_resistance,
)
from src.signals.strategies.base import BaseStrategy, StrategySignal, MarketRegime, TradeTiming


class MACDDivergence(BaseStrategy):
    name = "MACD Divergence"
    description = "Trade when price makes new high/low but MACD doesn't confirm — classic divergence"
    suitable_regimes = [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN,
                        MarketRegime.VOLATILE, MarketRegime.RANGING]
    suitable_assets = ["forex", "equity", "option"]
    expected_win_rate = 50.0
    expected_rr = 2.0

    def check_entry(self, df: pd.DataFrame, indicators: dict,
                    config: dict | None = None) -> StrategySignal | None:
        close = df["Close"]
        if len(close) < 40:
            return None

        price = float(close.iloc[-1])
        atr = indicators.get("atr") or price * 0.01
        rsi = indicators.get("rsi")
        macd = indicators.get("macd")

        if not macd:
            return None

        # Compute MACD series for divergence detection
        ema12 = compute_ema(close, 12)
        ema26 = compute_ema(close, 26)
        macd_line = ema12 - ema26
        signal_line = compute_ema(macd_line, 9)
        histogram = macd_line - signal_line

        if len(histogram) < 20:
            return None

        sr = find_support_resistance(df)

        for direction in ("BUY", "SELL"):
            met = []
            failed = []

            if direction == "BUY":
                # Bullish divergence: price makes lower low, MACD makes higher low
                # Check last 10 bars for a lower price low
                recent_lows = df["Low"].iloc[-10:]
                prior_lows = df["Low"].iloc[-20:-10]

                price_lower_low = float(recent_lows.min()) < float(prior_lows.min())
                macd_higher_low = float(histogram.iloc[-10:].min()) > float(histogram.iloc[-20:-10].min())

                if price_lower_low and macd_higher_low:
                    met.append("Bullish MACD divergence (price lower low, MACD higher low)")
                else:
                    # Also check simpler: MACD crossing up from negative
                    if macd.get("crossover"):
                        met.append("MACD bullish crossover")
                    elif macd.get("histogram", 0) > 0 and float(histogram.iloc[-2]) <= 0:
                        met.append("MACD histogram turned positive")
                    else:
                        continue

                if rsi and rsi < 50:
                    met.append(f"RSI has room to rise ({rsi:.0f})")
                else:
                    failed.append("RSI elevated")

                # Check if near support
                supports = sr.get("support", [])
                near_support = any(abs(price - s) / price < 0.03 for s in supports)
                if near_support:
                    met.append("Near support level")

                if len(met) < 2:
                    continue

                stop = price - atr * 1.5
                resistances = [r for r in sr.get("resistance", []) if r > price]
                target_1 = resistances[0] if resistances else price + atr * 3
                target_2 = price + atr * 4

            else:  # SELL
                recent_highs = df["High"].iloc[-10:]
                prior_highs = df["High"].iloc[-20:-10]

                price_higher_high = float(recent_highs.max()) > float(prior_highs.max())
                macd_lower_high = float(histogram.iloc[-10:].max()) < float(histogram.iloc[-20:-10].max())

                if price_higher_high and macd_lower_high:
                    met.append("Bearish MACD divergence (price higher high, MACD lower high)")
                else:
                    if macd.get("crossunder"):
                        met.append("MACD bearish crossunder")
                    elif macd.get("histogram", 0) < 0 and float(histogram.iloc[-2]) >= 0:
                        met.append("MACD histogram turned negative")
                    else:
                        continue

                if rsi and rsi > 50:
                    met.append(f"RSI has room to fall ({rsi:.0f})")
                else:
                    failed.append("RSI low")

                resistances = sr.get("resistance", [])
                near_resistance = any(abs(price - r) / price < 0.03 for r in resistances)
                if near_resistance:
                    met.append("Near resistance level")

                if len(met) < 2:
                    continue

                stop = price + atr * 1.5
                supports = [s for s in sr.get("support", []) if s < price]
                target_1 = supports[0] if supports else price - atr * 3
                target_2 = price - atr * 4

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
                confidence=self._confidence(met, 3),
                conditions_met=met,
                conditions_failed=failed,
                expected_win_rate=self.expected_win_rate,
                indicators_used={"rsi": rsi, "macd": macd, "atr": atr},
            )
            sig.compute_rr()
            sig.timing = TradeTiming(
                hold_duration="3-7 days",
                time_horizon="swing",
                best_entry_window="Enter on MACD histogram flip or crossover confirmation — wait for the turn, don't front-run",
                time_stop_bars=10,
                urgency="Divergences can take 2-5 bars to resolve — be patient but enter within 2 days of the signal",
                when_to_exit="Exit at next support/resistance level. Also exit if MACD histogram reverses direction against your trade.",
            )
            sig.explanation = self._build_explanation(met, failed, direction)
            return sig

        return None
