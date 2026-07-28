"""Strategy 6: IV Premium Selling — sell credit spreads when IV is rich (options only)."""

import pandas as pd

from src.analysis.technicals import compute_rsi, compute_atr, compute_ema
from src.signals.strategies.base import BaseStrategy, StrategySignal, MarketRegime, TradeTiming


class IVPremiumSelling(BaseStrategy):
    name = "IV Premium Sell"
    description = "Sell credit spreads when IV Rank > 50 — collect premium as it decays (Tastytrade method)"
    suitable_regimes = [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN,
                        MarketRegime.RANGING, MarketRegime.VOLATILE]
    suitable_assets = ["option"]
    expected_win_rate = 72.0
    expected_rr = 0.5

    def check_entry(self, df: pd.DataFrame, indicators: dict,
                    config: dict | None = None) -> StrategySignal | None:
        cfg = config or {}
        min_iv = cfg.get("min_iv_rank", 50)
        profit_target = cfg.get("profit_target_pct", 50)

        close = df["Close"]
        price = float(close.iloc[-1])
        iv_rank = indicators.get("iv_rank")
        rsi = indicators.get("rsi")
        atr = indicators.get("atr") or price * 0.01
        ema50 = compute_ema(close, 50)
        ema50_val = float(ema50.iloc[-1]) if len(ema50) >= 50 else price

        if iv_rank is None:
            return None

        met = []
        failed = []

        # Condition 1: IV Rank high enough
        if iv_rank >= min_iv:
            met.append(f"IV Rank elevated ({iv_rank:.0f}%)")
        else:
            return None  # Core condition

        # Determine direction bias for spread placement
        above_ema = price > ema50_val
        if above_ema:
            direction = "BUY"  # Bull put spread (sell below market)
            strategy_type = "bull put spread"
        else:
            direction = "SELL"  # Bear call spread (sell above market)
            strategy_type = "bear call spread"

        # Condition 2: Not at extreme RSI
        if rsi:
            if 25 < rsi < 75:
                met.append(f"RSI not extreme ({rsi:.0f})")
            else:
                failed.append(f"RSI at extreme ({rsi:.0f})")

        # Condition 3: ATR reasonable (need some movement for premium)
        atr_pct = (atr / price) * 100
        if atr_pct >= 0.5:
            met.append(f"Adequate volatility (ATR {atr_pct:.1f}%)")
        else:
            failed.append(f"Low volatility (ATR {atr_pct:.1f}%)")

        # Condition 4: IV rank in top half (higher = better for selling)
        if iv_rank >= 70:
            met.append(f"IV Rank very high ({iv_rank:.0f}%) — rich premium")

        if len(met) < 2:
            return None

        # Credit spread levels (approximate)
        # Short strike ~1 standard deviation OTM (~16 delta)
        std_dev_move = atr * 1.5  # Approximate 1 std dev

        if direction == "BUY":
            # Bull put spread: sell put below market
            short_strike = price - std_dev_move
            stop = short_strike  # Max loss at short strike
            # Credit ~ 1/3 of spread width
            est_credit = std_dev_move * 0.33
            target_1 = price  # We win if price stays above short strike
            target_2 = price + atr
        else:
            short_strike = price + std_dev_move
            stop = short_strike
            est_credit = std_dev_move * 0.33
            target_1 = price
            target_2 = price - atr

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
                             "strategy_type": strategy_type, "short_strike": round(short_strike, 2),
                             "est_credit": round(est_credit, 2)},
        )
        sig.compute_rr()
        sig.timing = TradeTiming(
            hold_duration="15-30 days (30-45 DTE entry, close at 21 DTE or 50% profit)",
            time_horizon="position",
            best_entry_window="Enter any time when IV Rank > 50 — not time-sensitive like directional trades",
            time_stop_bars=0,
            urgency="No rush — premium selling works best when you're patient. Enter this week.",
            when_to_exit="Close at 50% of max profit (if you collected $0.30, close when spread is worth $0.15). Also close at 21 DTE to avoid gamma risk near expiry. Stop loss: close if loss = 2x credit received.",
        )
        sig.explanation = (
            f"{self.name}: {strategy_type} on {df.index[-1].strftime('%Y-%m-%d') if hasattr(df.index[-1], 'strftime') else ''}. "
            f"IV Rank at {iv_rank:.0f}% means options premium is expensive — we sell it and collect as it decays. "
            f"Short strike at ~${short_strike:.0f} (1 std dev away). "
            f"Target: close at {profit_target}% of max profit. "
            + " ".join(f"{'✓' if c in met else '○'} {c}" for c in met + failed)
        )
        return sig
