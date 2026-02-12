"""Template-based indicator analysis — contextual text for each scoring indicator."""

from src.retrace.scoring_config import DEFAULT_WEIGHTS


def generate_indicator_analyses(
    ta: dict, scored: dict, price: float, symbol: str
) -> list[dict]:
    """Generate rich text analyses for all 6 scoring indicators.

    Returns a list of dicts, each containing:
        key, name, weight_pct, score, score_label, value_display,
        what_it_measures, current_reading, why_it_matters,
        score_explanation, trading_insight
    """
    weights = DEFAULT_WEIGHTS
    rsi = ta.get("rsi")
    trend = ta.get("trend")
    pivots = ta.get("pivots", {})
    atr = ta.get("atr")
    volume_ratio = ta.get("volume_ratio")
    gap_pct = ta.get("gap_pct")

    return [
        _analyze_rsi(rsi, weights.get("rsi", 0.20), symbol),
        _analyze_trend(trend, weights.get("trend", 0.15), symbol),
        _analyze_pivot(pivots, price, atr, weights.get("pivot", 0.20), symbol),
        _analyze_atr(atr, price, weights.get("atr", 0.20), symbol),
        _analyze_volume(volume_ratio, weights.get("volume", 0.15), symbol),
        _analyze_gap(gap_pct, volume_ratio, weights.get("gap", 0.10), symbol),
    ]


def _score_label(score: float) -> str:
    if score >= 80:
        return "Strong"
    if score >= 60:
        return "Good"
    if score >= 40:
        return "Neutral"
    if score >= 20:
        return "Weak"
    return "Poor"


# ── RSI ───────────────────────────────────────────────────────


def _rsi_component_score(rsi: float | None) -> float:
    if rsi is None:
        return 40
    if 30 <= rsi <= 50:
        return 80 + (50 - rsi) * 1.0
    if 50 < rsi <= 60:
        return 60
    if rsi < 30:
        return 70
    if rsi > 70:
        return 20
    return 50


def _analyze_rsi(rsi: float | None, weight: float, symbol: str) -> dict:
    score = _rsi_component_score(rsi)
    val_display = f"{rsi:.1f}" if rsi is not None else "N/A"

    what = (
        "RSI (Relative Strength Index) measures momentum on a 0-100 scale by comparing "
        "recent gains to recent losses over 14 periods. It identifies overbought conditions "
        "(above 70) and oversold conditions (below 30)."
    )

    if rsi is None:
        reading = f"RSI data is not available for {symbol}."
        why = "Without RSI, momentum cannot be assessed. Other indicators carry the weight."
        explanation = "No RSI data available — scored at neutral default (40)."
        insight = "Look to other indicators like trend and volume for directional clues."
    elif rsi > 70:
        reading = (
            f"{symbol} has an RSI of {rsi:.1f}, firmly in overbought territory. "
            "This means buyers have pushed prices aggressively and the move may be exhausted. "
            "Pullbacks are common from these levels."
        )
        why = (
            "Overbought RSI is a warning sign for day trades. Entering long at these levels "
            "carries elevated risk of a mean-reversion pullback that can hit stops quickly."
        )
        explanation = (
            f"RSI at {rsi:.1f} is overbought (>70), which scores poorly (20/100) because "
            "entering long into exhausted momentum increases the chance of a reversal."
        )
        insight = (
            "Avoid new long entries unless there is a clear catalyst. If already long, "
            "consider tightening stops. A short-side fade may develop if volume drops off."
        )
    elif 60 <= rsi <= 70:
        reading = (
            f"{symbol} has an RSI of {rsi:.1f}, in the upper-neutral zone approaching overbought. "
            "Momentum is bullish but nearing levels where buyers often take profits."
        )
        why = (
            "RSI in the 60-70 range shows decent momentum but isn't at the high-conviction "
            "bounce zone. Continuation is possible but the risk/reward is less favorable."
        )
        explanation = (
            f"RSI at {rsi:.1f} is in the 60-70 range — moderate momentum scored at 50/100. "
            "Not the ideal entry zone for fresh longs but not a warning sign either."
        )
        insight = (
            "Momentum is present but fading. Best for continuation plays with tight risk "
            "rather than new positions. Watch for RSI divergence as a reversal signal."
        )
    elif 50 < rsi < 60:
        reading = (
            f"{symbol} has an RSI of {rsi:.1f}, in a mildly bullish zone. Price has been "
            "gaining ground but hasn't reached overbought levels, leaving room to move higher."
        )
        why = (
            "Mid-range RSI is neutral territory. It doesn't strongly favor either direction "
            "but suggests the instrument isn't at extremes, which keeps risk manageable."
        )
        explanation = (
            f"RSI at {rsi:.1f} sits in the 50-60 range — scored at 60/100. Moderately "
            "bullish but not at the high-conviction recovery zone."
        )
        insight = (
            "Price has upward momentum without being stretched. Look for a pullback "
            "toward the 50 level as a potential entry opportunity with better risk/reward."
        )
    elif 30 <= rsi <= 50:
        dist = rsi - 30
        reading = (
            f"{symbol} has an RSI of {rsi:.1f}, in the recovery zone. Recent selling has "
            "brought the indicator to levels where bounces historically begin. "
            f"{'Close to oversold — strong bounce potential.' if dist < 10 else 'Room to run before overbought.'}"
        )
        why = (
            "The 30-50 RSI zone is the sweet spot for day-trade entries. Selling pressure "
            "has exhausted, but price hasn't rallied enough for profit-taking. This creates "
            "asymmetric risk/reward for long entries."
        )
        explanation = (
            f"RSI at {rsi:.1f} is in the ideal 30-50 recovery zone — scored at {score:.0f}/100. "
            "This zone gets the highest RSI scores because it offers the best bounce probability."
        )
        insight = (
            "This is the high-conviction zone. Look for price to hold support near current "
            "levels and enter on the first sign of buying pressure. Set stops below the "
            "recent swing low."
        )
    else:  # rsi < 30
        reading = (
            f"{symbol} has an RSI of {rsi:.1f}, deep in oversold territory. Heavy selling "
            "has driven the indicator below 30, signaling potential capitulation. "
            "Bounce potential is high but timing is uncertain."
        )
        why = (
            "Oversold RSI suggests a counter-trend bounce is likely but catching a falling "
            "knife is risky. The strongest trades come after RSI crosses back above 30, "
            "confirming the bottom."
        )
        explanation = (
            f"RSI at {rsi:.1f} is oversold (<30) — scored at 70/100. High bounce potential "
            "but slightly lower than the 30-50 zone because timing the exact bottom is difficult."
        )
        insight = (
            "Wait for RSI to tick back above 30 before entering. A bullish divergence "
            "(price makes a lower low but RSI makes a higher low) would be a strong signal. "
            "Use a wider stop to account for residual selling."
        )

    return {
        "key": "rsi",
        "name": "RSI Momentum",
        "weight_pct": round(weight * 100),
        "score": round(score),
        "score_label": _score_label(score),
        "value_display": val_display,
        "what_it_measures": what,
        "current_reading": reading,
        "why_it_matters": why,
        "score_explanation": explanation,
        "trading_insight": insight,
    }


# ── Trend ─────────────────────────────────────────────────────

_TREND_SCORES = {
    "bullish": 100,
    "weakly_bullish": 75,
    "neutral": 40,
    "weakly_bearish": 20,
    "bearish": 0,
}


def _analyze_trend(trend: str | None, weight: float, symbol: str) -> dict:
    t = trend or "neutral"
    score = _TREND_SCORES.get(t, 40)
    label = t.replace("_", " ").title()

    what = (
        "Trend alignment compares the 20-day and 50-day simple moving averages (SMA) "
        "relative to the current price. When price is above both averages and the short-term "
        "average is above the long-term, the trend is bullish."
    )

    templates = {
        "bullish": {
            "reading": (
                f"{symbol} is in a strong bullish trend — price is above both the 20-day and "
                "50-day SMAs, and the shorter average leads. Buyers are firmly in control."
            ),
            "why": (
                "Trading with a strong trend dramatically improves win rates. Pullbacks tend "
                "to find support at the moving averages, giving clear entry levels."
            ),
            "explanation": (
                "Full bullish alignment (price > SMA20 > SMA50) scores 100/100. "
                "This is the highest conviction trend configuration."
            ),
            "insight": (
                "Use pullbacks to the 20-day SMA as entry opportunities. The trend supports "
                "holding through minor dips. Add to winners rather than booking early profits."
            ),
        },
        "weakly_bullish": {
            "reading": (
                f"{symbol} shows a weakly bullish trend — the 20-day SMA is above the 50-day, "
                "but price hasn't fully committed above both. Momentum is building."
            ),
            "why": (
                "A developing uptrend offers opportunity but needs confirmation. Price may "
                "oscillate around the moving averages before committing to a direction."
            ),
            "explanation": (
                "Weak bullish (SMA20 > SMA50 but price not above both) scores 75/100. "
                "Positive structure but lacking full confirmation."
            ),
            "insight": (
                "Wait for price to close above the 20-day SMA for a higher-probability entry. "
                "A break above the nearest resistance with volume would confirm the trend."
            ),
        },
        "neutral": {
            "reading": (
                f"{symbol} is in a neutral trend — the moving averages are converging and price "
                "is oscillating around them. No clear directional bias exists."
            ),
            "why": (
                "Neutral trends make day trading harder because breakouts in either direction "
                "can fail. Range-bound strategies work better than trend-following here."
            ),
            "explanation": (
                "Neutral trend (averages converging) scores 40/100. Without directional "
                "alignment, trade setups are less reliable."
            ),
            "insight": (
                "Focus on support/resistance levels for range-bound trades. Avoid trend-following "
                "entries until the moving averages separate. Reduce position sizes."
            ),
        },
        "weakly_bearish": {
            "reading": (
                f"{symbol} shows a weakly bearish trend — the 50-day SMA has crossed above the "
                "20-day, suggesting sellers are gaining influence. Caution is warranted."
            ),
            "why": (
                "A developing downtrend means long entries are counter-trend trades with lower "
                "probabilities. Rallies tend to be sold into, making targets harder to reach."
            ),
            "explanation": (
                "Weak bearish (SMA50 > SMA20) scores 20/100. Structural deterioration "
                "makes long day trades risky."
            ),
            "insight": (
                "If trading long, use tight stops and quick profit targets. Consider sitting "
                "out until the trend improves or look for short-side setups."
            ),
        },
        "bearish": {
            "reading": (
                f"{symbol} is in a strong bearish trend — price is below both SMAs with the "
                "50-day above the 20-day. Sellers dominate and rallies are consistently sold."
            ),
            "why": (
                "Trading against a strong bearish trend is the lowest-probability setup. "
                "Even attractive RSI readings can be traps as price grinds lower."
            ),
            "explanation": (
                "Full bearish alignment (price < SMA20 < SMA50) scores 0/100. "
                "This is the worst environment for long day trades."
            ),
            "insight": (
                "Avoid long entries entirely. If you must trade, only consider short-side "
                "setups on bounces to resistance. Capital preservation is the priority."
            ),
        },
    }

    tmpl = templates.get(t, templates["neutral"])

    return {
        "key": "trend",
        "name": "Trend Alignment",
        "weight_pct": round(weight * 100),
        "score": round(score),
        "score_label": _score_label(score),
        "value_display": label,
        "what_it_measures": what,
        "current_reading": tmpl["reading"],
        "why_it_matters": tmpl["why"],
        "score_explanation": tmpl["explanation"],
        "trading_insight": tmpl["insight"],
    }


# ── Pivot Proximity ───────────────────────────────────────────


def _pivot_component_score(price: float, pivots: dict, atr: float | None) -> float:
    if not pivots or not price or price <= 0:
        return 40
    s1 = pivots.get("s1")
    r1 = pivots.get("r1")
    if s1 is None or r1 is None:
        return 40
    threshold = (atr or price * 0.01) * 0.5
    if s1 > 0 and abs(price - s1) <= threshold:
        return 90
    if r1 > 0 and price > r1 and (price - r1) <= threshold:
        return 85
    return 40


def _analyze_pivot(
    pivots: dict, price: float, atr: float | None, weight: float, symbol: str
) -> dict:
    score = _pivot_component_score(price, pivots, atr)
    p = pivots.get("pivot")
    r1 = pivots.get("r1")
    s1 = pivots.get("s1")

    if p is not None:
        val_display = f"P:{p:.2f} R1:{r1:.2f} S1:{s1:.2f}"
    else:
        val_display = "N/A"

    what = (
        "Pivot points are calculated from the previous day's high, low, and close. They "
        "define key levels where price is likely to find support (S1, S2) or resistance "
        "(R1, R2). The central pivot (P) acts as the day's directional bias."
    )

    if not pivots or p is None:
        reading = f"Pivot data is unavailable for {symbol}."
        why = "Without pivot levels, support and resistance must be estimated from other methods."
        explanation = "No pivot data — scored at neutral default (40)."
        insight = "Use the SMA levels and prior swing highs/lows as proxy support and resistance."
    else:
        threshold = (atr or price * 0.01) * 0.5
        near_s1 = s1 and abs(price - s1) <= threshold
        above_r1 = r1 and price > r1 and (price - r1) <= threshold

        if near_s1:
            reading = (
                f"{symbol} is trading near S1 support at ${s1:.2f} (price: ${price:.2f}). "
                "This is a recognized bounce level where buyers often step in."
            )
            why = (
                "Proximity to S1 creates a natural long entry with a well-defined stop below S1. "
                "The pivot acts as the first target, giving a measurable risk/reward."
            )
            explanation = (
                f"Price near S1 (${s1:.2f}) scores 90/100 — a classic pivot bounce setup "
                "with clear entry, stop, and target levels."
            )
            insight = (
                f"Enter near ${s1:.2f} with a stop ${(threshold * 2):.2f} below. "
                f"First target is the pivot at ${p:.2f}, second target R1 at ${r1:.2f}."
            )
        elif above_r1:
            reading = (
                f"{symbol} has broken above R1 at ${r1:.2f} (price: ${price:.2f}). "
                "This breakout above resistance signals strong buying pressure."
            )
            why = (
                "R1 breakouts with momentum can lead to moves toward R2. "
                "The breakout level (R1) often becomes new support."
            )
            explanation = (
                f"Price breaking above R1 (${r1:.2f}) scores 85/100 — momentum breakout "
                "setup with the former resistance as the new stop level."
            )
            r2 = pivots.get("r2")
            r2_str = f"${r2:.2f}" if r2 else "R2"
            insight = (
                f"Use R1 at ${r1:.2f} as your stop level. Target R2 at {r2_str}. "
                "Volume confirmation on the break increases reliability."
            )
        else:
            pos = "above" if price > p else "below"
            reading = (
                f"{symbol} at ${price:.2f} is {pos} the pivot at ${p:.2f}, in mid-range "
                f"between S1 (${s1:.2f}) and R1 (${r1:.2f}). Not near a key level."
            )
            why = (
                "Mid-range price relative to pivots means no clear edge from support/resistance. "
                "The best pivot setups occur near S1 (bounce) or R1 (breakout)."
            )
            explanation = (
                "Price in mid-range between pivots scores 40/100 — no proximity-based edge. "
                "Wait for price to approach S1 or R1 for a higher-score setup."
            )
            insight = (
                f"Wait for a pullback to S1 (${s1:.2f}) or a push through R1 (${r1:.2f}) "
                "before entering. Mid-range entries lack a clear technical anchor."
            )

    return {
        "key": "pivot",
        "name": "Pivot Proximity",
        "weight_pct": round(weight * 100),
        "score": round(score),
        "score_label": _score_label(score),
        "value_display": val_display,
        "what_it_measures": what,
        "current_reading": reading,
        "why_it_matters": why,
        "score_explanation": explanation,
        "trading_insight": insight,
    }


# ── ATR Volatility ────────────────────────────────────────────


def _atr_component_score(atr: float | None, price: float) -> float:
    if atr is None or price <= 0:
        return 40
    atr_pct = (atr / price) * 100
    if atr_pct >= 2.0:
        return 100
    if atr_pct >= 1.5:
        return 80
    if atr_pct >= 1.0:
        return 60
    if atr_pct >= 0.5:
        return 40
    return 20


def _analyze_atr(atr: float | None, price: float, weight: float, symbol: str) -> dict:
    score = _atr_component_score(atr, price)
    atr_pct = (atr / price) * 100 if atr and price > 0 else None
    val_display = f"${atr:.4f} ({atr_pct:.1f}%)" if atr and atr_pct else "N/A"

    what = (
        "ATR (Average True Range) measures the average daily price range over 14 periods. "
        "It quantifies volatility — higher ATR means bigger daily moves. For day trading, "
        "sufficient volatility is essential to generate profit within a single session."
    )

    if atr is None or price <= 0:
        reading = f"ATR data is unavailable for {symbol}."
        why = "Without volatility data, position sizing and profit targets cannot be calibrated."
        explanation = "No ATR data — scored at neutral default (40)."
        insight = "Use recent price range visually to estimate volatility before entering."
    elif atr_pct >= 2.0:
        reading = (
            f"{symbol} has an ATR of ${atr:.2f} ({atr_pct:.1f}% of price). This is high "
            "volatility — the instrument typically moves more than 2% per day, providing "
            "ample room for intraday profit."
        )
        why = (
            "High ATR means targets can be set further from entry while still being achievable "
            "in a single session. This is ideal for day trades with wide target ranges."
        )
        explanation = (
            f"ATR at {atr_pct:.1f}% of price is high volatility (>=2%) — scores 100/100. "
            "Maximum score because the daily range easily accommodates 1:2+ risk/reward setups."
        )
        insight = (
            "Size your position smaller to account for the wider stops required. "
            f"A reasonable stop is 0.5x ATR (${atr * 0.5:.2f}) and target 1x ATR (${atr:.2f})."
        )
    elif atr_pct >= 1.5:
        reading = (
            f"{symbol} has an ATR of ${atr:.2f} ({atr_pct:.1f}% of price). Good volatility "
            "that supports intraday trading with reasonable target distances."
        )
        why = (
            "1.5-2% daily range is the sweet spot — enough movement for profit but not so "
            "volatile that stops are constantly triggered by noise."
        )
        explanation = (
            f"ATR at {atr_pct:.1f}% is good volatility (1.5-2%) — scores 80/100. "
            "Well-suited for day trade setups."
        )
        insight = (
            f"Standard stop placement at 0.5x ATR (${atr * 0.5:.2f}). "
            "This volatility level works well with pivot-based targets."
        )
    elif atr_pct >= 1.0:
        reading = (
            f"{symbol} has an ATR of ${atr:.2f} ({atr_pct:.1f}% of price). Moderate "
            "volatility that may require patience for intraday moves to develop."
        )
        why = (
            "Moderate ATR means smaller profit potential per trade. Positions may need "
            "to be held longer, and commission costs are a larger percentage of profit."
        )
        explanation = (
            f"ATR at {atr_pct:.1f}% is moderate (1.0-1.5%) — scores 60/100. "
            "Workable but not ideal for day trading."
        )
        insight = (
            "Consider slightly larger position sizes (since stops are tighter) or "
            "look for catalyst events that could expand the daily range."
        )
    elif atr_pct >= 0.5:
        reading = (
            f"{symbol} has an ATR of ${atr:.2f} ({atr_pct:.1f}% of price). Low volatility "
            "means the typical daily range is small, making intraday profit targets tight."
        )
        why = (
            "Low volatility instruments are challenging for day trading. The small range "
            "means targets are close to entry, reducing potential reward."
        )
        explanation = (
            f"ATR at {atr_pct:.1f}% is low (0.5-1.0%) — scores 40/100. "
            "Daily movement is limited for meaningful intraday setups."
        )
        insight = (
            "This may be better suited for swing trades. If day trading, use very tight "
            "stops and look for gap or news catalysts to expand the range."
        )
    else:
        reading = (
            f"{symbol} has an ATR of ${atr:.2f} ({atr_pct:.1f}% of price). Very low "
            "volatility — the instrument barely moves intraday."
        )
        why = (
            "Very low volatility makes day trading impractical. The potential profit "
            "is too small to justify the time and transaction costs."
        )
        explanation = (
            f"ATR at {atr_pct:.1f}% is very low (<0.5%) — scores 20/100. "
            "Insufficient movement for day trade profitability."
        )
        insight = (
            "Skip this instrument for day trades. Consider swing or position trades "
            "on higher timeframes where the cumulative range is more meaningful."
        )

    return {
        "key": "atr",
        "name": "ATR Volatility",
        "weight_pct": round(weight * 100),
        "score": round(score),
        "score_label": _score_label(score),
        "value_display": val_display,
        "what_it_measures": what,
        "current_reading": reading,
        "why_it_matters": why,
        "score_explanation": explanation,
        "trading_insight": insight,
    }


# ── Volume ────────────────────────────────────────────────────


def _volume_component_score(volume_ratio: float | None) -> float:
    if volume_ratio is None:
        return 40
    if volume_ratio >= 2.0:
        return 100
    if volume_ratio >= 1.5:
        return 80
    if volume_ratio >= 1.0:
        return 60
    if volume_ratio >= 0.8:
        return 40
    return 20


def _analyze_volume(volume_ratio: float | None, weight: float, symbol: str) -> dict:
    score = _volume_component_score(volume_ratio)
    val_display = f"{volume_ratio:.2f}x avg" if volume_ratio is not None else "N/A"

    what = (
        "Volume ratio compares today's volume to the 20-day average. A ratio above 1.0 "
        "means above-average participation. High volume validates price moves and increases "
        "the reliability of breakouts and bounces."
    )

    if volume_ratio is None:
        reading = f"Volume data is unavailable for {symbol}."
        why = "Without volume confirmation, it's harder to assess the conviction behind price moves."
        explanation = "No volume data — scored at neutral default (40)."
        insight = "Pay extra attention to price action at key levels since volume can't confirm moves."
    elif volume_ratio >= 2.0:
        reading = (
            f"{symbol} is trading at {volume_ratio:.1f}x average volume. This is significantly "
            "elevated participation — institutional or event-driven activity is likely."
        )
        why = (
            "Very high volume confirms that price moves are backed by conviction. "
            "Breakouts with this volume level are far more likely to follow through."
        )
        explanation = (
            f"Volume at {volume_ratio:.1f}x average (>=2x) scores 100/100. "
            "Exceptional participation confirms any price signals."
        )
        insight = (
            "High-conviction setup. Breakouts and pivots are more reliable today. "
            "The elevated volume may also mean wider intraday swings — use it to your advantage."
        )
    elif volume_ratio >= 1.5:
        reading = (
            f"{symbol} is trading at {volume_ratio:.1f}x average volume. Above-average "
            "participation suggests heightened interest from market participants."
        )
        why = (
            "Moderately elevated volume supports the validity of today's price action. "
            "Moves are more likely to sustain rather than quickly reverse."
        )
        explanation = (
            f"Volume at {volume_ratio:.1f}x average (1.5-2x) scores 80/100. "
            "Good participation that confirms price direction."
        )
        insight = (
            "Volume supports directional plays. Combine with trend and RSI signals "
            "for higher confidence. Breakouts above R1 with this volume tend to hold."
        )
    elif volume_ratio >= 1.0:
        reading = (
            f"{symbol} is trading at {volume_ratio:.1f}x average volume. Participation is "
            "normal — neither especially strong nor weak."
        )
        why = (
            "Average volume means price moves are occurring with normal market interest. "
            "Signals aren't amplified or negated by volume conditions."
        )
        explanation = (
            f"Volume at {volume_ratio:.1f}x average (1.0-1.5x) scores 60/100. "
            "Normal participation — neither a boost nor a drag on signals."
        )
        insight = (
            "Volume is supportive but not exceptional. Standard risk management applies. "
            "Look for volume to increase on a breakout as confirmation before committing."
        )
    elif volume_ratio >= 0.8:
        reading = (
            f"{symbol} is trading at {volume_ratio:.1f}x average volume. Slightly below "
            "average — participation is tepid today."
        )
        why = (
            "Below-average volume means less conviction behind moves. Breakouts are more "
            "likely to fail and reversals may lack follow-through."
        )
        explanation = (
            f"Volume at {volume_ratio:.1f}x average (0.8-1.0x) scores 40/100. "
            "Weak participation reduces reliability of technical signals."
        )
        insight = (
            "Be cautious with breakout entries — low volume fakeouts are common. "
            "Consider smaller positions or wait for volume to pick up before entering."
        )
    else:
        reading = (
            f"{symbol} is trading at {volume_ratio:.1f}x average volume. Very low "
            "participation — the market is quiet on this instrument today."
        )
        why = (
            "Very low volume makes all price moves suspect. Spreads may be wider "
            "and fills less reliable. Avoid day trading in thin conditions."
        )
        explanation = (
            f"Volume at {volume_ratio:.1f}x average (<0.8x) scores 20/100. "
            "Insufficient participation for reliable day trading."
        )
        insight = (
            "Skip this instrument today or wait for a volume catalyst. "
            "Thin markets can whipsaw stops without any real directional move."
        )

    return {
        "key": "volume",
        "name": "Volume Activity",
        "weight_pct": round(weight * 100),
        "score": round(score),
        "score_label": _score_label(score),
        "value_display": val_display,
        "what_it_measures": what,
        "current_reading": reading,
        "why_it_matters": why,
        "score_explanation": explanation,
        "trading_insight": insight,
    }


# ── Gap Analysis ──────────────────────────────────────────────


def _gap_component_score(gap_pct: float | None, volume_ratio: float | None) -> float:
    if gap_pct is None:
        return 50
    abs_gap = abs(gap_pct)
    vol_ok = (volume_ratio or 1.0) >= 1.0
    if 0.5 <= abs_gap <= 2.0 and vol_ok:
        return 90
    if abs_gap <= 0.5:
        return 50
    if abs_gap > 3.0:
        return 30
    return 60


def _analyze_gap(
    gap_pct: float | None, volume_ratio: float | None, weight: float, symbol: str
) -> dict:
    score = _gap_component_score(gap_pct, volume_ratio)
    if gap_pct is not None:
        direction = "up" if gap_pct > 0 else "down"
        val_display = f"{gap_pct:+.2f}% ({direction})"
    else:
        val_display = "N/A"

    what = (
        "Gap analysis measures the difference between today's open and yesterday's close as "
        "a percentage. Gaps signal overnight sentiment shifts — news, earnings, or global "
        "events. The gap size and accompanying volume determine its trading significance."
    )

    if gap_pct is None:
        reading = f"Gap data is unavailable for {symbol}."
        why = "Without gap data, overnight sentiment cannot be assessed."
        explanation = "No gap data — scored at neutral default (50)."
        insight = "Check the opening range manually for any overnight price dislocation."
    else:
        abs_gap = abs(gap_pct)
        direction = "up" if gap_pct > 0 else "down"
        vol_ok = (volume_ratio or 1.0) >= 1.0

        if abs_gap <= 0.5:
            reading = (
                f"{symbol} opened with a minimal gap of {gap_pct:+.2f}%. "
                "The market opened roughly where it closed — no significant overnight shift."
            )
            why = (
                "Minimal gaps are neutral. They don't provide extra momentum but also "
                "don't create gap-fill dynamics that can trap traders."
            )
            explanation = (
                f"Gap of {gap_pct:+.2f}% is minimal (<=0.5%) — scores 50/100. "
                "Neither a catalyst nor a headwind."
            )
            insight = (
                "No gap-driven setup available. Focus on other indicators like RSI, "
                "trend, and pivot levels for trade decisions."
            )
        elif 0.5 < abs_gap <= 2.0 and vol_ok:
            reading = (
                f"{symbol} gapped {direction} {abs_gap:.1f}% on {volume_ratio:.1f}x average "
                f"volume. This is a momentum gap — significant enough to signal direction "
                "but not so large that it's already extended."
            )
            why = (
                "Moderate gaps with volume are the highest-probability gap plays. "
                "They show institutional conviction without excessive extension. "
                "Continuation in the gap direction is the favored play."
            )
            explanation = (
                f"Gap of {gap_pct:+.2f}% with {volume_ratio:.1f}x volume scores 90/100. "
                "The ideal gap size (0.5-2%) with confirming volume."
            )
            insight = (
                f"Trade in the direction of the gap ({direction}). The gap level "
                "(yesterday's close) becomes a key stop reference — if price fills "
                "the gap, the momentum thesis is invalidated."
            )
        elif 0.5 < abs_gap <= 2.0:
            reading = (
                f"{symbol} gapped {direction} {abs_gap:.1f}% but volume is below average. "
                "The gap direction may not have strong conviction behind it."
            )
            why = (
                "Gaps without volume support are more likely to fill (reverse). "
                "Low-volume gaps often represent thin-market noise rather than true sentiment."
            )
            explanation = (
                f"Gap of {gap_pct:+.2f}% without volume support scores 60/100. "
                "The right size but lacking participation confirmation."
            )
            insight = (
                "Consider a gap-fill trade (opposite direction) if price starts to "
                "reverse. Alternatively, wait for volume to confirm before trading the gap direction."
            )
        elif abs_gap > 3.0:
            reading = (
                f"{symbol} gapped {direction} {abs_gap:.1f}% — a large dislocation, likely "
                "driven by earnings, news, or a macro event. Price opened far from fair value."
            )
            why = (
                "Very large gaps are risky. While they show strong sentiment, the move "
                "may already be priced in. Gap-fill (partial or full) is common after "
                "the initial euphoria or panic subsides."
            )
            explanation = (
                f"Gap of {gap_pct:+.2f}% is extended (>3%) — scores 30/100. "
                "Elevated risk of reversal makes fresh entries dangerous."
            )
            insight = (
                "Avoid chasing the gap direction. Wait for price to consolidate or "
                "fill partially before entering. If trading, use tight stops and "
                "expect high volatility. The first 30 minutes will set the tone."
            )
        else:  # 2-3% without strong volume
            reading = (
                f"{symbol} gapped {direction} {abs_gap:.1f}%. A notable gap that shows "
                "clear overnight sentiment shift."
            )
            why = (
                "Larger gaps (2-3%) carry moderate risk. Continuation is possible but "
                "partial gap-fills are common, creating choppy price action."
            )
            explanation = (
                f"Gap of {gap_pct:+.2f}% (2-3% range) scores 60/100. "
                "Significant but carries reversal risk."
            )
            insight = (
                "Look for the gap to hold its first 15-minute range before entering. "
                "If the gap range holds, continuation is likely. If it breaks, "
                "a gap-fill move becomes the higher-probability trade."
            )

    return {
        "key": "gap",
        "name": "Gap Analysis",
        "weight_pct": round(weight * 100),
        "score": round(score),
        "score_label": _score_label(score),
        "value_display": val_display,
        "what_it_measures": what,
        "current_reading": reading,
        "why_it_matters": why,
        "score_explanation": explanation,
        "trading_insight": insight,
    }
