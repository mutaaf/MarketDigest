"""Strategy 7: Opening Range Breakout — buy options on inside day breakouts."""

import pandas as pd

from src.analysis.technicals import detect_inside_day
from src.signals.strategies.base import BaseStrategy, MarketRegime, StrategySignal, TradeTiming


class ORBDirectional(BaseStrategy):
    name = "Range Breakout"
    description = "Buy calls/puts on inside day breakouts with cheap options (IV < 40)"
    suitable_regimes = [MarketRegime.LOW_VOLATILITY, MarketRegime.VOLATILE]
    suitable_assets = ["option"]
    expected_win_rate = 47.0
    expected_rr = 2.0

    def check_entry(self, df: pd.DataFrame, indicators: dict,
                    config: dict | None = None) -> StrategySignal | None:
        cfg = config or {}
        max_iv = cfg.get("max_iv_rank", 40)

        close = df["Close"]
        if len(close) < 5:
            return None

        price = float(close.iloc[-1])
        atr = indicators.get("atr") or price * 0.01
        iv_rank = indicators.get("iv_rank")
        rsi = indicators.get("rsi")

        # Core condition: yesterday was inside day
        is_inside = detect_inside_day(df)
        if not is_inside:
            return None

        # Prior day's range
        yest_high = float(df["High"].iloc[-2])
        yest_low = float(df["Low"].iloc[-2])

        met = []
        failed = []

        met.append("Inside day detected (compression)")

        # Check which direction broke out
        if price > yest_high:
            direction = "BUY"
            met.append(f"Price broke above yesterday's high ({yest_high:.2f})")
        elif price < yest_low:
            direction = "SELL"
            met.append(f"Price broke below yesterday's low ({yest_low:.2f})")
        else:
            return None  # No breakout yet

        # IV Rank check (want cheap options for directional buying)
        if iv_rank is not None:
            if iv_rank <= max_iv:
                met.append(f"IV Rank low ({iv_rank:.0f}%) — options are cheap")
            else:
                failed.append(f"IV Rank high ({iv_rank:.0f}%) — options expensive")

        # ATR check
        atr_pct = (atr / price) * 100
        if atr_pct >= 0.5:
            met.append(f"Sufficient volatility (ATR {atr_pct:.1f}%)")
        else:
            failed.append(f"Low volatility (ATR {atr_pct:.1f}%)")

        if len(met) < 3:
            return None

        if direction == "BUY":
            stop = yest_high - atr * 0.3  # Just below breakout level
            target_1 = price + atr * 2
            target_2 = price + atr * 3
        else:
            stop = yest_low + atr * 0.3
            target_1 = price - atr * 2
            target_2 = price - atr * 3

        risk = abs(price - stop)
        reward = abs(target_1 - price)
        if risk <= 0 or reward / risk < 1.5:
            return None

        sig = StrategySignal(
            direction=direction,
            entry_price=round(price, 2),
            stop_loss=round(stop, 2),
            target_1=round(target_1, 2),
            target_2=round(target_2, 2),
            strategy_name=self.name,
            confidence=self._confidence(met, 4),
            conditions_met=met,
            conditions_failed=failed,
            expected_win_rate=self.expected_win_rate,
            indicators_used={"iv_rank": iv_rank, "rsi": rsi, "atr": atr,
                             "inside_day": True, "yest_high": yest_high,
                             "yest_low": yest_low},
        )
        sig.compute_rr()
        sig.timing = TradeTiming(
            hold_duration="1-5 days",
            time_horizon="short-term swing",
            best_entry_window="Enter on breakout close today — inside day breaks are intraday events",
            time_stop_bars=5,
            urgency="Act today — inside day breakouts lose their edge after 2-3 days",
            when_to_exit="Target: 100% gain on option premium (double your money). Stop: exit if underlying closes back inside yesterday's range. Time stop: 5 trading days max.",
        )
        sig.explanation = self._build_explanation(met, failed, direction)
        return sig
