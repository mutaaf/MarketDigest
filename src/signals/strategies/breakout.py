"""Strategy 3: Donchian Channel Breakout — trade range breaks from compression."""

import pandas as pd

from src.analysis.technicals import (
    compute_rsi, compute_atr, compute_donchian, compute_donchian_exit,
    compute_bollinger_bands, compute_volume_ratio,
)
from src.signals.strategies.base import BaseStrategy, StrategySignal, MarketRegime, TradeTiming


class DonchianBreakout(BaseStrategy):
    name = "Donchian Breakout"
    description = "Buy 20-day high breakouts from volatility squeezes (Turtle Trading inspired)"
    suitable_regimes = [MarketRegime.LOW_VOLATILITY, MarketRegime.VOLATILE]
    suitable_assets = ["forex", "equity", "option"]
    expected_win_rate = 38.0
    expected_rr = 3.0

    def should_filter(self, df: pd.DataFrame, indicators: dict) -> tuple[bool, str]:
        rsi = indicators.get("rsi")
        if rsi and rsi > 80:
            return True, f"RSI too high ({rsi:.0f}) — extended, breakout likely to fail"
        return False, ""

    def check_entry(self, df: pd.DataFrame, indicators: dict,
                    config: dict | None = None) -> StrategySignal | None:
        cfg = config or {}
        channel_period = cfg.get("channel_period", 20)
        exit_period = cfg.get("exit_period", 10)
        min_vol_ratio = cfg.get("min_volume_ratio", 1.2)
        max_squeeze_bars = cfg.get("max_squeeze_bars", 5)

        close = df["Close"]
        price = float(close.iloc[-1])
        high = float(df["High"].iloc[-1])
        low = float(df["Low"].iloc[-1])
        atr = indicators.get("atr") or price * 0.01

        donchian = compute_donchian(df, channel_period)
        donchian_exit = compute_donchian_exit(df, exit_period)
        if not donchian or not donchian_exit:
            return None

        vol_ratio = indicators.get("volume_ratio")
        bb = indicators.get("bollinger")

        # Check if recent squeeze existed
        was_squeeze = False
        if bb:
            for i in range(1, min(max_squeeze_bars + 1, len(close))):
                bb_prev = compute_bollinger_bands(close.iloc[:-i] if i > 0 else close, 20, 2.0)
                if bb_prev and bb_prev.get("squeeze", False):
                    was_squeeze = True
                    break

        bar_range = high - low
        close_position = (price - low) / bar_range if bar_range > 0 else 0.5

        for direction in ("BUY", "SELL"):
            met = []
            failed = []

            if direction == "BUY":
                # Condition 1: Close above 20-day high
                if price >= donchian["upper"]:
                    met.append(f"Close above 20-day high ({donchian['upper']:.4f})")
                else:
                    continue

                # Condition 2: Recent squeeze
                if was_squeeze:
                    met.append("Recent BB squeeze (volatility expansion)")
                else:
                    failed.append("No recent squeeze")

                # Condition 3: Volume confirmation
                if vol_ratio and vol_ratio >= min_vol_ratio:
                    met.append(f"Volume {vol_ratio:.1f}x average")
                elif vol_ratio:
                    failed.append(f"Low volume ({vol_ratio:.1f}x)")

                # Condition 4: Strong close (upper 25% of range)
                if close_position >= 0.75:
                    met.append(f"Strong close ({close_position:.0%} of range)")
                else:
                    failed.append(f"Weak close ({close_position:.0%} of range)")

                if len(met) < 2:
                    continue

                stop = donchian_exit["lower"]  # 10-day low (Turtle exit)
                target_1 = price + abs(price - stop) * 2
                target_2 = price + abs(price - stop) * 3

            else:  # SELL
                if price <= donchian["lower"]:
                    met.append(f"Close below 20-day low ({donchian['lower']:.4f})")
                else:
                    continue

                if was_squeeze:
                    met.append("Recent BB squeeze (volatility expansion)")
                else:
                    failed.append("No recent squeeze")

                if vol_ratio and vol_ratio >= min_vol_ratio:
                    met.append(f"Volume {vol_ratio:.1f}x average")
                elif vol_ratio:
                    failed.append(f"Low volume ({vol_ratio:.1f}x)")

                if close_position <= 0.25:
                    met.append(f"Weak close ({close_position:.0%} of range)")
                else:
                    failed.append(f"Not weak enough close")

                if len(met) < 2:
                    continue

                stop = donchian_exit["upper"]
                target_1 = price - abs(stop - price) * 2
                target_2 = price - abs(stop - price) * 3

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
                indicators_used={"donchian": donchian, "vol_ratio": vol_ratio,
                                 "was_squeeze": was_squeeze, "close_position": close_position},
            )
            sig.compute_rr()
            sig.timing = TradeTiming(
                hold_duration="5-20 days (let winners run)",
                time_horizon="swing to position",
                best_entry_window="Enter on breakout close — needs daily candle confirmation above the channel",
                time_stop_bars=0,
                urgency="Act on today's close if breakout confirmed — false breakouts reverse fast",
                when_to_exit="No fixed target — trail stop using 10-day low (Turtle exit). Let the trend carry you. Only exit when price closes below 10-day low.",
            )
            sig.explanation = self._build_explanation(met, failed, direction)
            return sig

        return None
