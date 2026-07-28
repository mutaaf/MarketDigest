"""Strategy 2: Bollinger Band Mean Reversion — buy at lower band in ranging markets."""

import pandas as pd

from src.signals.strategies.base import BaseStrategy, MarketRegime, StrategySignal, TradeTiming


class BollingerMeanReversion(BaseStrategy):
    name = "BB Mean Reversion"
    description = "Buy at lower Bollinger Band / sell at upper in ranging markets (ADX < 30)"
    suitable_regimes = [MarketRegime.RANGING]
    suitable_assets = ["forex", "equity", "option"]
    expected_win_rate = 62.0
    expected_rr = 1.3

    def should_filter(self, df: pd.DataFrame, indicators: dict) -> tuple[bool, str]:
        adx = indicators.get("adx")
        if adx is not None and adx > 30:
            return True, f"ADX too high ({adx}) — trending market, mean reversion fails"

        # Check for breakdown: 3 consecutive closes below lower BB
        bb = indicators.get("bollinger")
        if bb:
            close = df["Close"]
            lower = bb["lower"]
            if len(close) >= 3:
                last3 = [float(close.iloc[-i]) for i in range(1, 4)]
                if all(c < lower for c in last3):
                    return True, "3 consecutive closes below lower BB — breakdown, not mean reversion"
        return False, ""

    def check_entry(self, df: pd.DataFrame, indicators: dict,
                    config: dict | None = None) -> StrategySignal | None:
        cfg = config or {}
        entry_pct_b = cfg.get("entry_pct_b", 0.05)
        rsi_threshold = cfg.get("rsi_threshold", 35)
        min_bandwidth = cfg.get("min_bandwidth", 2.0)

        close = df["Close"]
        price = float(close.iloc[-1])
        bb = indicators.get("bollinger")
        rsi = indicators.get("rsi")
        stoch = indicators.get("stochastic")
        atr = indicators.get("atr") or price * 0.01

        if not bb:
            return None

        for direction in ("BUY", "SELL"):
            met = []
            failed = []

            if direction == "BUY":
                # Condition 1: Price at or below lower BB
                if bb["pct_b"] <= entry_pct_b:
                    met.append(f"Price at lower BB (%B={bb['pct_b']:.2f})")
                elif bb["pct_b"] <= 0.2:
                    met.append(f"Price near lower BB (%B={bb['pct_b']:.2f})")
                else:
                    continue

                # Condition 2: RSI confirms oversold
                if rsi and rsi < rsi_threshold:
                    met.append(f"RSI oversold ({rsi:.0f})")
                elif rsi and rsi < 45:
                    met.append(f"RSI leaning oversold ({rsi:.0f})")
                else:
                    failed.append(f"RSI not oversold ({rsi:.0f})" if rsi else "No RSI")

                # Condition 3: Stochastic turning up
                if stoch and stoch["k"] < 30:
                    if stoch.get("d") and stoch["k"] > stoch["d"]:
                        met.append(f"Stochastic turning up (K={stoch['k']:.0f} > D={stoch['d']:.0f})")
                    else:
                        met.append(f"Stochastic oversold (K={stoch['k']:.0f})")
                else:
                    failed.append("Stochastic not oversold")

                # Condition 4: Bandwidth sufficient for reversion profit
                if bb["bandwidth"] >= min_bandwidth:
                    met.append(f"BB width sufficient ({bb['bandwidth']:.1f}%)")
                else:
                    failed.append(f"BB too narrow ({bb['bandwidth']:.1f}%)")

                if len(met) < 3:
                    continue

                stop = bb["lower"] - atr * 0.5
                target_1 = bb["middle"]  # Mean reversion target = middle BB
                target_2 = bb["upper"] * 0.95  # Near upper band

            else:  # SELL
                if bb["pct_b"] >= (1 - entry_pct_b):
                    met.append(f"Price at upper BB (%B={bb['pct_b']:.2f})")
                elif bb["pct_b"] >= 0.8:
                    met.append(f"Price near upper BB (%B={bb['pct_b']:.2f})")
                else:
                    continue

                if rsi and rsi > (100 - rsi_threshold):
                    met.append(f"RSI overbought ({rsi:.0f})")
                elif rsi and rsi > 55:
                    met.append(f"RSI leaning overbought ({rsi:.0f})")
                else:
                    failed.append("RSI not overbought" if rsi else "No RSI")

                if stoch and stoch["k"] > 70:
                    if stoch.get("d") and stoch["k"] < stoch["d"]:
                        met.append(f"Stochastic turning down (K={stoch['k']:.0f} < D={stoch['d']:.0f})")
                    else:
                        met.append(f"Stochastic overbought (K={stoch['k']:.0f})")
                else:
                    failed.append("Stochastic not overbought")

                if bb["bandwidth"] >= min_bandwidth:
                    met.append(f"BB width sufficient ({bb['bandwidth']:.1f}%)")
                else:
                    failed.append(f"BB too narrow ({bb['bandwidth']:.1f}%)")

                if len(met) < 3:
                    continue

                stop = bb["upper"] + atr * 0.5
                target_1 = bb["middle"]
                target_2 = bb["lower"] * 1.05

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
                indicators_used={"bb": bb, "rsi": rsi, "stoch": stoch, "atr": atr},
            )
            sig.compute_rr()
            sig.timing = TradeTiming(
                hold_duration="1-5 days",
                time_horizon="swing",
                best_entry_window="Enter at daily close or next open — band touches are end-of-day signals",
                time_stop_bars=7,
                urgency="Enter today if conditions met — mean reversion setups decay quickly",
                when_to_exit="Close entire position at middle Bollinger Band (SMA 20). If price doesn't reach middle band within 5 days, exit at close.",
            )
            sig.explanation = self._build_explanation(met, failed, direction)
            return sig

        return None
