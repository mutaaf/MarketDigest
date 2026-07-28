"""Strategy 1: EMA Trend Following — buy pullbacks in confirmed trends."""

import pandas as pd

from src.analysis.technicals import (
    compute_ema,
    find_support_resistance,
)
from src.signals.strategies.base import BaseStrategy, MarketRegime, StrategySignal, TradeTiming


class EMATrendFollow(BaseStrategy):
    name = "EMA Trend Follow"
    description = "Buy pullbacks to the 21 EMA in confirmed uptrends (stacked EMAs + ADX > 25)"
    suitable_regimes = [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]
    suitable_assets = ["forex", "equity", "option"]
    expected_win_rate = 42.0
    expected_rr = 2.5

    def should_filter(self, df: pd.DataFrame, indicators: dict) -> tuple[bool, str]:
        adx = indicators.get("adx")
        if adx is not None and adx < 20:
            return True, f"ADX too low ({adx}) — no trend"
        atr = indicators.get("atr")
        price = float(df["Close"].iloc[-1])
        if atr and price > 0 and (atr / price * 100) < 0.3:
            return True, "ATR too low — insufficient volatility"
        return False, ""

    def check_entry(self, df: pd.DataFrame, indicators: dict,
                    config: dict | None = None) -> StrategySignal | None:
        cfg = config or {}
        fast_p = cfg.get("ema_fast", 9)
        slow_p = cfg.get("ema_slow", 21)
        trend_p = cfg.get("ema_trend", 50)
        pullback_mult = cfg.get("pullback_atr_mult", 0.5)
        stop_mult = cfg.get("stop_atr_mult", 1.5)

        close = df["Close"]
        if len(close) < trend_p + 5:
            return None

        price = float(close.iloc[-1])
        ema_fast = compute_ema(close, fast_p)
        ema_slow = compute_ema(close, slow_p)
        ema_trend = compute_ema(close, trend_p)

        ef = float(ema_fast.iloc[-1])
        es = float(ema_slow.iloc[-1])
        et = float(ema_trend.iloc[-1])
        atr = indicators.get("atr") or price * 0.01
        rsi = indicators.get("rsi")

        met = []
        failed = []

        # Check both BUY and SELL setups
        for direction in ("BUY", "SELL"):
            met = []
            failed = []

            if direction == "BUY":
                # Condition 1: Stacked EMAs (fast > slow > trend)
                if ef > es > et:
                    met.append("EMAs stacked bullish (9>21>50)")
                else:
                    failed.append("EMAs not stacked bullish")
                    continue

                # Condition 2: Price pulled back to 21 EMA
                pullback_zone = es + atr * pullback_mult
                if price <= pullback_zone:
                    met.append(f"Price pulled back near 21 EMA ({es:.4f})")
                else:
                    failed.append(f"Price too far above 21 EMA ({price:.4f} vs {pullback_zone:.4f})")
                    continue

                # Condition 3: RSI between 40-60 (pullback reset momentum)
                if rsi and 40 <= rsi <= 60:
                    met.append(f"RSI in pullback zone ({rsi:.0f})")
                elif rsi:
                    failed.append(f"RSI not in pullback zone ({rsi:.0f})")

                # Condition 4: Current bar closes above fast EMA
                if price > ef:
                    met.append("Close above 9 EMA (pullback ending)")
                else:
                    failed.append("Close below 9 EMA")

                # Need at least 3/4 conditions
                if len(met) < 3:
                    continue

                # Compute levels from structure
                stop = max(et, price - atr * stop_mult)  # Below 50 EMA or ATR stop
                if stop >= price:
                    stop = price - atr * stop_mult

                # Target from next resistance or 2R
                sr = find_support_resistance(df)
                resistances = [r for r in sr.get("resistance", []) if r > price]
                target_1 = resistances[0] if resistances else price + abs(price - stop) * 2
                target_2 = resistances[1] if len(resistances) > 1 else price + abs(price - stop) * 3

            else:  # SELL
                if ef < es < et:
                    met.append("EMAs stacked bearish (9<21<50)")
                else:
                    failed.append("EMAs not stacked bearish")
                    continue

                pullback_zone = es - atr * pullback_mult
                if price >= pullback_zone:
                    met.append(f"Price pulled back near 21 EMA ({es:.4f})")
                else:
                    failed.append("Price too far below 21 EMA")
                    continue

                if rsi and 40 <= rsi <= 60:
                    met.append(f"RSI in pullback zone ({rsi:.0f})")
                elif rsi:
                    failed.append(f"RSI not in pullback zone ({rsi:.0f})")

                if price < ef:
                    met.append("Close below 9 EMA (pullback ending)")
                else:
                    failed.append("Close above 9 EMA")

                if len(met) < 3:
                    continue

                stop = min(et, price + atr * stop_mult)
                if stop <= price:
                    stop = price + atr * stop_mult

                sr = find_support_resistance(df)
                supports = [s for s in sr.get("support", []) if s < price]
                target_1 = supports[0] if supports else price - abs(stop - price) * 2
                target_2 = supports[1] if len(supports) > 1 else price - abs(stop - price) * 3

            # Validate R/R
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
                indicators_used={"ema_fast": ef, "ema_slow": es, "ema_trend": et,
                                 "rsi": rsi, "atr": atr},
            )
            sig.compute_rr()
            sig.timing = TradeTiming(
                hold_duration="3-10 days",
                time_horizon="swing",
                best_entry_window="Enter on daily close confirmation or next day open",
                time_stop_bars=15,
                urgency="Wait for today's close to confirm — don't chase",
                when_to_exit="Close 50% at Target 1 (2R). Trail stop on rest using 21 EMA — exit when price closes below 21 EMA.",
            )
            sig.explanation = self._build_explanation(met, failed, direction)
            return sig

        return None
