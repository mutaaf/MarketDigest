"""Strategy 4: RSI Momentum Continuation — buy extreme short-term dips in uptrends."""

import pandas as pd

from src.analysis.technicals import compute_rsi, compute_sma
from src.signals.strategies.base import BaseStrategy, MarketRegime, StrategySignal, TradeTiming


class RSIMomentum(BaseStrategy):
    name = "RSI Momentum"
    description = "Buy when RSI(2) hits extreme oversold in long-term uptrend (Connors RSI)"
    suitable_regimes = [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN, MarketRegime.VOLATILE]
    suitable_assets = ["equity", "option"]
    expected_win_rate = 57.0
    expected_rr = 1.5

    def should_filter(self, df: pd.DataFrame, indicators: dict) -> tuple[bool, str]:
        rsi14 = indicators.get("rsi")
        if rsi14 and rsi14 > 70:
            return True, f"RSI(14) overbought ({rsi14:.0f}) — long-term overextended"
        return False, ""

    def check_entry(self, df: pd.DataFrame, indicators: dict,
                    config: dict | None = None) -> StrategySignal | None:
        cfg = config or {}
        rsi_short_period = cfg.get("rsi_short_period", 2)
        rsi_threshold = cfg.get("rsi_threshold", 10)
        sma_period = cfg.get("sma_trend_period", 200)

        close = df["Close"]
        if len(close) < max(sma_period, 20):
            return None

        price = float(close.iloc[-1])
        atr = indicators.get("atr") or price * 0.01

        # RSI(2) — very short-term momentum
        rsi2 = compute_rsi(close, rsi_short_period)
        rsi2_val = float(rsi2.iloc[-1]) if not rsi2.empty else None

        # 200 SMA for long-term trend
        sma200 = compute_sma(close, sma_period)
        sma200_val = float(sma200.iloc[-1]) if sma200 is not None and len(sma200) >= sma_period else None

        # 5 SMA for exit target
        sma5 = compute_sma(close, 5)
        sma5_val = float(sma5.iloc[-1]) if sma5 is not None else price

        macd = indicators.get("macd")

        for direction in ("BUY", "SELL"):
            met = []
            failed = []

            if direction == "BUY":
                # Condition 1: Price above 200 SMA (long-term uptrend)
                if sma200_val and price > sma200_val:
                    met.append(f"Above 200 SMA ({sma200_val:.2f}) — long-term uptrend")
                else:
                    continue  # Don't buy against the long-term trend

                # Condition 2: RSI(2) extreme oversold
                if rsi2_val is not None and rsi2_val < rsi_threshold:
                    met.append(f"RSI(2) extreme oversold ({rsi2_val:.0f})")
                else:
                    continue  # This is the core trigger

                # Condition 3: Today's low < yesterday's low (active selling)
                if len(df) >= 2:
                    today_low = float(df["Low"].iloc[-1])
                    yest_low = float(df["Low"].iloc[-2])
                    if today_low < yest_low:
                        met.append("Lower low (active selling into dip)")
                    else:
                        failed.append("No lower low")

                # Condition 4: MACD histogram decelerating (selling slowing)
                if macd:
                    hist = macd.get("histogram", 0)
                    if hist < 0:
                        met.append("MACD negative (momentum still weak)")
                    else:
                        met.append("MACD positive (momentum turning)")

                if len(met) < 3:
                    continue

                # Stop below 3-bar swing low
                recent_lows = [float(df["Low"].iloc[-i]) for i in range(1, min(4, len(df)))]
                stop = min(recent_lows) - atr * 0.3

                # Target: close above 5 SMA
                target_1 = sma5_val if sma5_val > price else price + atr
                target_2 = price + atr * 2

            else:  # SELL
                if sma200_val and price < sma200_val:
                    met.append(f"Below 200 SMA ({sma200_val:.2f}) — long-term downtrend")
                else:
                    continue

                if rsi2_val is not None and rsi2_val > (100 - rsi_threshold):
                    met.append(f"RSI(2) extreme overbought ({rsi2_val:.0f})")
                else:
                    continue

                if len(df) >= 2:
                    today_high = float(df["High"].iloc[-1])
                    yest_high = float(df["High"].iloc[-2])
                    if today_high > yest_high:
                        met.append("Higher high (active buying into rally)")
                    else:
                        failed.append("No higher high")

                if macd:
                    if macd.get("histogram", 0) > 0:
                        met.append("MACD positive (momentum still strong)")
                    else:
                        met.append("MACD negative (momentum turning)")

                if len(met) < 3:
                    continue

                recent_highs = [float(df["High"].iloc[-i]) for i in range(1, min(4, len(df)))]
                stop = max(recent_highs) + atr * 0.3
                target_1 = sma5_val if sma5_val < price else price - atr
                target_2 = price - atr * 2

            risk = abs(price - stop)
            reward = abs(target_1 - price)
            if risk <= 0 or reward / risk < 1.0:
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
                indicators_used={"rsi2": rsi2_val, "sma200": sma200_val,
                                 "sma5": sma5_val, "macd": macd},
            )
            sig.compute_rr()
            sig.timing = TradeTiming(
                hold_duration="1-5 days (typically 2-3)",
                time_horizon="short-term swing",
                best_entry_window="Enter at today's close or tomorrow's open — RSI(2) extremes resolve within 1-5 bars",
                time_stop_bars=5,
                urgency="Enter today — RSI(2) signals are time-sensitive and lose edge after 1-2 days",
                when_to_exit="Exit when price closes above the 5-day SMA. If it doesn't within 5 days, exit at close regardless (time stop).",
            )
            sig.explanation = self._build_explanation(met, failed, direction)
            return sig

        return None
