"""Day-trade scoring — rank instruments by intraday opportunity."""


GRADE_SCALE = [
    (90, "A+"), (85, "A"), (80, "A-"),
    (75, "B+"), (70, "B"), (65, "B-"),
    (60, "C+"), (55, "C"), (50, "C-"),
    (40, "D"),
]


def score_to_grade(score: float) -> str:
    """Convert a numeric score (0-100) to a letter grade."""
    for threshold, grade in GRADE_SCALE:
        if score >= threshold:
            return grade
    return "F"


def _score_rsi(rsi: float | None) -> float:
    """RSI momentum score (0-100). Sweet spot is recovery zone 30-50."""
    if rsi is None:
        return 40
    if 30 <= rsi <= 50:
        return 80 + (50 - rsi) * 1.0  # 80-100, peaks near 30
    if 50 < rsi <= 60:
        return 60
    if rsi < 30:
        return 70  # oversold bounce potential
    if rsi > 70:
        return 20  # overbought, avoid
    return 50  # 60-70 range


def _score_trend(trend: str | None) -> float:
    """Trend alignment score (0-100)."""
    mapping = {
        "bullish": 100,
        "weakly_bullish": 75,
        "neutral": 40,
        "weakly_bearish": 20,
        "bearish": 0,
    }
    return mapping.get(trend or "neutral", 40)


def _score_pivot_proximity(price: float, pivots: dict, atr: float | None) -> float:
    """Score based on proximity to pivot levels (0-100)."""
    if not pivots or not price or price <= 0:
        return 40
    s1 = pivots.get("s1")
    r1 = pivots.get("r1")
    if s1 is None or r1 is None:
        return 40

    threshold = (atr or price * 0.01) * 0.5

    # Near S1 — bounce setup
    if s1 > 0 and abs(price - s1) <= threshold:
        return 90
    # Breaking above R1 — momentum
    if r1 > 0 and price > r1 and (price - r1) <= threshold:
        return 85
    # Mid-range
    return 40


def _score_atr(atr: float | None, price: float) -> float:
    """ATR volatility score (0-100). Day trades need volatility."""
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


def _score_volume(volume_ratio: float | None) -> float:
    """Volume score (0-100). Higher relative volume = better."""
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


def _score_gap(gap_pct: float | None, volume_ratio: float | None) -> float:
    """Gap score (0-100). Moderate gap with volume = momentum."""
    if gap_pct is None:
        return 50
    abs_gap = abs(gap_pct)
    vol_ok = (volume_ratio or 1.0) >= 1.0

    if 0.5 <= abs_gap <= 2.0 and vol_ok:
        return 90  # momentum gap with volume
    if abs_gap <= 0.5:
        return 50  # minimal gap
    if abs_gap > 3.0:
        return 30  # extended, risky
    # gap 2-3% without strong volume
    return 60


def _build_signals(ta: dict, price: float) -> list[str]:
    """Build human-readable signal list (top reasons)."""
    signals = []
    rsi = ta.get("rsi")
    trend = ta.get("trend")
    volume_ratio = ta.get("volume_ratio")
    gap_pct = ta.get("gap_pct")
    pivots = ta.get("pivots", {})

    if rsi is not None:
        if 30 <= rsi <= 50:
            signals.append(f"RSI bounce ({rsi:.0f})")
        elif rsi < 30:
            signals.append(f"Oversold RSI ({rsi:.0f})")
        elif rsi > 70:
            signals.append(f"Overbought RSI ({rsi:.0f})")

    if trend in ("bullish", "weakly_bullish"):
        signals.append(f"Trend: {trend.replace('_', ' ')}")

    if volume_ratio is not None and volume_ratio >= 1.5:
        signals.append(f"Vol {volume_ratio:.1f}x avg")

    r1 = pivots.get("r1")
    s1 = pivots.get("s1")
    if r1 and price > r1:
        signals.append("Breaking R1")
    elif s1 and price and abs(price - s1) / max(price, 0.01) < 0.005:
        signals.append("Near S1 support")

    if gap_pct is not None and abs(gap_pct) >= 0.5:
        direction = "up" if gap_pct > 0 else "down"
        signals.append(f"Gap {direction} {abs(gap_pct):.1f}%")

    return signals[:3]


def score_instrument(ta: dict, price_data: dict, weights: dict | None = None) -> dict | None:
    """Score a single instrument for day-trade potential.

    Args:
        ta: Technical analysis dict from full_analysis().
        price_data: Price dict with price, name, etc.
        weights: Optional explicit scoring weights. If None, loads from config/scoring.yaml.

    Returns:
        Dict with symbol, score, entry/target/stop, signals, risk_reward.
        None if insufficient data.
    """
    if ta.get("error") or not price_data:
        return None

    price = price_data.get("price")
    if not price or price <= 0:
        return None

    rsi = ta.get("rsi")
    trend = ta.get("trend")
    pivots = ta.get("pivots", {})
    atr = ta.get("atr")
    volume_ratio = ta.get("volume_ratio")
    gap_pct = ta.get("gap_pct")

    # Weighted composite score
    if weights is None:
        from src.retrace.scoring_config import load_scoring_weights
        weights = load_scoring_weights()
    scores = {
        "rsi": _score_rsi(rsi),
        "trend": _score_trend(trend),
        "pivot": _score_pivot_proximity(price, pivots, atr),
        "atr": _score_atr(atr, price),
        "volume": _score_volume(volume_ratio),
        "gap": _score_gap(gap_pct, volume_ratio),
    }
    composite = sum(scores[k] * weights[k] for k in weights)

    # Entry / target / stop
    s1 = pivots.get("s1", price * 0.99)
    r1 = pivots.get("r1", price * 1.01)
    atr_val = atr or price * 0.01

    entry = price
    target = max(r1, price + atr_val)
    stop = max(s1, price - 0.5 * atr_val)

    # Determine pivot level labels
    target_level = "R1" if target == r1 else "ATR"
    stop_level = "S1" if stop == s1 else "ATR"

    # Avoid division by zero
    risk = entry - stop
    reward = target - entry
    risk_reward = round(reward / risk, 2) if risk > 0 else 0.0

    rounded_score = round(composite, 1)

    return {
        "symbol": ta.get("ticker", price_data.get("ticker", "?")),
        "name": price_data.get("name", ta.get("name", "?")),
        "score": rounded_score,
        "grade": score_to_grade(rounded_score),
        "entry": round(entry, 2),
        "target": round(target, 2),
        "stop": round(stop, 2),
        "target_level": target_level,
        "stop_level": stop_level,
        "signals": _build_signals(ta, price),
        "risk_reward": risk_reward,
        "atr_pct": round((atr / price) * 100, 1) if atr and price > 0 else None,
        "rsi": rsi,
        "trend": trend,
        "trend_emoji": ta.get("trend_emoji", ""),
        "volume_ratio": volume_ratio,
        "price": round(price, 2),
    }


def get_condensed_track_record(symbol: str) -> dict | None:
    """W-L summary from retrace grading history.

    Returns {wins, losses, win_rate, avg_r} or None if no graded history.
    """
    from src.retrace.snapshot import list_snapshots, load_snapshot

    metas = list_snapshots(limit=100)
    wins = 0
    losses = 0
    r_multiples: list[float] = []

    for meta in metas:
        if not meta.get("has_grading"):
            continue
        if meta.get("digest_type", "daytrade") != "daytrade":
            continue
        snap = load_snapshot(meta["date"])
        if not snap or not snap.get("grading"):
            continue

        for pick in snap["grading"].get("picks", []):
            if pick.get("symbol") != symbol:
                continue
            outcome = pick.get("outcome", "pending")
            if outcome == "win":
                wins += 1
            elif outcome == "loss":
                losses += 1
            r = pick.get("r_multiple")
            if r is not None:
                r_multiples.append(r)

    total = wins + losses
    if total == 0:
        return None

    return {
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / total * 100, 1),
        "avg_r": round(sum(r_multiples) / len(r_multiples), 2) if r_multiples else None,
    }


def rank_daytrade_picks(scored: list[dict], top_n: int = 10) -> list[dict]:
    """Sort scored instruments descending by score, return top N."""
    valid = [s for s in scored if s is not None]
    valid.sort(key=lambda x: x["score"], reverse=True)
    return valid[:top_n]
