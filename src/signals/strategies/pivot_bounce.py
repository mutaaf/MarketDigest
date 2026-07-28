"""Strategy 5: Pivot Point Bounce — trade reversals at daily pivot levels."""

import pandas as pd

from src.analysis.technicals import (
    compute_rsi, compute_atr, compute_pivot_points, compute_adx,
    compute_ema, detect_reversal_candle,
)
from src.signals.strategies.base import BaseStrategy, StrategySignal, MarketRegime, TradeTiming


class PivotBounce(BaseStrategy):
    name = "Pivot Bounce"
    description = "Buy at S1 support with reversal candle confirmation (floor trader method)"
    suitable_regimes = [MarketRegime.RANGING, MarketRegime.TRENDING_UP]
    suitable_assets = ["forex", "equity"]
    expected_win_rate = 52.0
    expected_rr = 2.0

    def should_filter(self, df: pd.DataFrame, indicators: dict) -> tuple[bool, str]:
        adx = indicators.get("adx")
        if adx and adx > 35:
            # Strong trend — pivots get blown through
            ema50 = compute_ema(df["Close"], 50)
            price = float(df["Close"].iloc[-1])
            if price < float(ema50.iloc[-1]):
                return True, f"Strong downtrend (ADX={adx}) — pivots unreliable"
        return False, ""

    def check_entry(self, df: pd.DataFrame, indicators: dict,
                    config: dict | None = None) -> StrategySignal | None:
        cfg = config or {}
        prox_mult = cfg.get("proximity_atr_mult", 0.3)
        stop_mult = cfg.get("stop_atr_mult", 0.5)

        close = df["Close"]
        price = float(close.iloc[-1])
        atr = indicators.get("atr") or price * 0.01
        rsi = indicators.get("rsi")
        pivots = indicators.get("pivots", {})
        candle = detect_reversal_candle(df)

        if not pivots:
            return None

        s1 = pivots.get("s1")
        s2 = pivots.get("s2")
        r1 = pivots.get("r1")
        r2 = pivots.get("r2")
        pivot = pivots.get("pivot")

        if not all([s1, r1, pivot]):
            return None

        threshold = atr * prox_mult

        for direction in ("BUY", "SELL"):
            met = []
            failed = []

            if direction == "BUY":
                # Condition 1: Price near S1
                if abs(price - s1) <= threshold:
                    met.append(f"Price near S1 ({s1:.4f})")
                elif s2 and abs(price - s2) <= threshold:
                    met.append(f"Price near S2 ({s2:.4f})")
                else:
                    continue

                # Condition 2: Bullish reversal candle
                if candle["bullish"]:
                    detail = "hammer" if candle.get("hammer") else "bullish close"
                    met.append(f"Reversal candle ({detail})")
                else:
                    failed.append("No bullish reversal candle")

                # Condition 3: RSI < 50 (room to bounce)
                if rsi and rsi < 50:
                    met.append(f"RSI has room ({rsi:.0f})")
                elif rsi:
                    failed.append(f"RSI too high ({rsi:.0f})")

                # Condition 4: Not below S2 (structure intact)
                if s2 and price > s2:
                    met.append("Above S2 (pivot structure intact)")
                elif s2:
                    failed.append("Below S2 (structure broken)")

                if len(met) < 3:
                    continue

                stop = s1 - atr * stop_mult
                target_1 = pivot  # Central pivot
                target_2 = r1

            else:  # SELL
                if abs(price - r1) <= threshold:
                    met.append(f"Price near R1 ({r1:.4f})")
                elif r2 and abs(price - r2) <= threshold:
                    met.append(f"Price near R2 ({r2:.4f})")
                else:
                    continue

                if candle["bearish"]:
                    detail = "shooting star" if candle.get("shooting_star") else "bearish close"
                    met.append(f"Reversal candle ({detail})")
                else:
                    failed.append("No bearish reversal candle")

                if rsi and rsi > 50:
                    met.append(f"RSI has room ({rsi:.0f})")
                elif rsi:
                    failed.append(f"RSI too low ({rsi:.0f})")

                if r2 and price < r2:
                    met.append("Below R2 (pivot structure intact)")
                elif r2:
                    failed.append("Above R2 (structure broken)")

                if len(met) < 3:
                    continue

                stop = r1 + atr * stop_mult
                target_1 = pivot
                target_2 = s1

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
                indicators_used={"pivots": pivots, "rsi": rsi, "candle": candle, "atr": atr},
            )
            sig.compute_rr()
            sig.timing = TradeTiming(
                hold_duration="1-3 days",
                time_horizon="short-term swing",
                best_entry_window="Enter on the reversal candle close or next bar open — pivot bounces work best intraday to next-day",
                time_stop_bars=5,
                urgency="Act today — pivot levels reset daily, this setup is only valid for 1-2 days",
                when_to_exit="Take profit at central Pivot (P) level. If price reaches R1/S1 on the other side, that's bonus. Exit by end of day 3 if neither target nor stop hit.",
            )
            sig.explanation = self._build_explanation(met, failed, direction)
            return sig

        return None
