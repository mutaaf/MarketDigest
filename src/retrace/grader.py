"""Retrace grader — grade day trade picks against actual next-day prices."""

from datetime import datetime, timedelta

from src.utils.logging_config import get_logger

logger = get_logger("retrace.grader")


def _get_next_trading_day_data(symbol: str, pick_date: str) -> dict | None:
    """Fetch next-trading-day OHLCV for a symbol after pick_date."""
    try:
        import yfinance as yf
        from datetime import datetime, timedelta

        dt = datetime.strptime(pick_date, "%Y-%m-%d")
        # Fetch a window to ensure we capture the next trading day
        start = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
        end = (dt + timedelta(days=7)).strftime("%Y-%m-%d")

        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start, end=end)
        if hist.empty:
            return None

        row = hist.iloc[0]
        return {
            "date": str(hist.index[0].date()),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row["Volume"]) if row["Volume"] else 0,
        }
    except Exception as e:
        logger.debug(f"Failed to fetch next-day data for {symbol}: {e}")
        return None


def grade_single_pick(pick: dict, next_day: dict) -> dict:
    """Grade a single pick against next-day OHLCV data.

    Returns grading dict with outcome, MFE, MAE, r_multiple, etc.
    """
    entry = pick.get("entry", 0)
    target = pick.get("target", 0)
    stop = pick.get("stop", 0)

    if not entry or not target or not next_day:
        return {"outcome": "pending", "reason": "insufficient data"}

    high = next_day["high"]
    low = next_day["low"]
    close = next_day["close"]
    open_price = next_day["open"]

    hit_target = high >= target
    hit_stop = low <= stop

    # MFE / MAE (from entry)
    mfe = high - entry  # max favorable excursion
    mae = entry - low   # max adverse excursion
    actual_return = close - entry

    # R-multiple (risk = entry - stop)
    risk = entry - stop if entry > stop else entry * 0.01
    r_multiple = round(actual_return / risk, 2) if risk > 0 else 0.0

    # Determine outcome
    if hit_target and not hit_stop:
        outcome = "win"
    elif hit_stop and not hit_target:
        outcome = "loss"
    elif hit_target and hit_stop:
        # Both hit — ambiguous without intraday data
        outcome = "ambiguous"
    else:
        # Neither hit — scratch (close to entry)
        pct_move = abs(actual_return / entry) * 100 if entry > 0 else 0
        outcome = "scratch" if pct_move < 0.5 else ("win" if actual_return > 0 else "loss")

    return {
        "outcome": outcome,
        "next_day_date": next_day["date"],
        "next_day_open": round(open_price, 2),
        "next_day_high": round(high, 2),
        "next_day_low": round(low, 2),
        "next_day_close": round(close, 2),
        "hit_target": hit_target,
        "hit_stop": hit_stop,
        "mfe": round(mfe, 2),
        "mae": round(mae, 2),
        "actual_return": round(actual_return, 2),
        "actual_return_pct": round((actual_return / entry) * 100, 2) if entry > 0 else 0,
        "r_multiple": r_multiple,
    }


def grade_snapshot(snapshot: dict) -> dict:
    """Grade all picks in a snapshot against actual next-day prices.

    Modifies the snapshot in place and returns the grading summary.
    """
    pick_date = snapshot.get("date")
    if not pick_date:
        return {"error": "No date in snapshot"}

    # Check if next trading day has passed
    try:
        dt = datetime.strptime(pick_date, "%Y-%m-%d")
        if datetime.now() - dt < timedelta(days=1):
            return {"error": "Next trading day hasn't occurred yet"}
    except ValueError:
        return {"error": f"Invalid date: {pick_date}"}

    all_picks = snapshot.get("top_picks", []) + snapshot.get("honorable_mentions", [])
    graded_picks = []
    outcomes = {"win": 0, "loss": 0, "scratch": 0, "ambiguous": 0, "pending": 0}

    for pick in all_picks:
        symbol = pick.get("symbol")
        if not symbol:
            continue

        next_day = _get_next_trading_day_data(symbol, pick_date)
        if next_day:
            grading = grade_single_pick(pick, next_day)
        else:
            grading = {"outcome": "pending", "reason": "no next-day data"}

        graded_picks.append({
            "symbol": symbol,
            "score": pick.get("score"),
            "entry": pick.get("entry"),
            "target": pick.get("target"),
            "stop": pick.get("stop"),
            "signals": pick.get("signals", []),
            "trend": pick.get("trend"),
            **grading,
        })
        outcomes[grading.get("outcome", "pending")] += 1

    total = outcomes["win"] + outcomes["loss"] + outcomes["scratch"]
    win_rate = round(outcomes["win"] / total * 100, 1) if total > 0 else 0

    grading_summary = {
        "graded_at": datetime.now().isoformat(),
        "picks": graded_picks,
        "total_graded": total,
        "outcomes": outcomes,
        "win_rate": win_rate,
        "avg_r_multiple": round(
            sum(p.get("r_multiple", 0) for p in graded_picks if p.get("outcome") in ("win", "loss", "scratch"))
            / max(total, 1), 2
        ),
    }

    # Save back to snapshot (use snapshot_id for new-format files, fallback to date for legacy)
    snapshot["grading"] = grading_summary
    from src.retrace.snapshot import save_snapshot_data
    snapshot_id = snapshot.get("snapshot_id", pick_date)
    save_snapshot_data(snapshot_id, snapshot)

    logger.info(f"Graded {pick_date}: {outcomes['win']}W/{outcomes['loss']}L/{outcomes['scratch']}S — {win_rate}% WR")
    return grading_summary


def aggregate_performance(snapshots: list[dict], days: int = 30) -> dict:
    """Aggregate performance across multiple graded snapshots."""
    total_wins = 0
    total_losses = 0
    total_scratches = 0
    total_ambiguous = 0
    r_multiples = []
    by_signal: dict[str, dict] = {}
    by_trend: dict[str, dict] = {}
    all_picks: list[dict] = []
    timeline: list[dict] = []

    cutoff = datetime.now() - timedelta(days=days)

    for snap in snapshots:
        try:
            snap_date = datetime.strptime(snap.get("date", ""), "%Y-%m-%d")
        except ValueError:
            continue
        if snap_date < cutoff:
            continue

        grading = snap.get("grading")
        if not grading:
            continue

        outcomes = grading.get("outcomes", {})
        wins = outcomes.get("win", 0)
        losses = outcomes.get("loss", 0)
        scratches = outcomes.get("scratch", 0)

        total_wins += wins
        total_losses += losses
        total_scratches += scratches
        total_ambiguous += outcomes.get("ambiguous", 0)

        day_total = wins + losses + scratches
        timeline.append({
            "date": snap.get("date"),
            "wins": wins,
            "losses": losses,
            "scratches": scratches,
            "win_rate": round(wins / day_total * 100, 1) if day_total > 0 else 0,
            "avg_r": grading.get("avg_r_multiple", 0),
        })

        for pick in grading.get("picks", []):
            outcome = pick.get("outcome")
            if outcome not in ("win", "loss", "scratch"):
                continue

            r_multiples.append(pick.get("r_multiple", 0))
            all_picks.append({
                "date": snap.get("date"),
                **pick,
            })

            # By signal
            for signal in pick.get("signals", []):
                key = signal.split("(")[0].strip()  # e.g. "RSI bounce" from "RSI bounce (42)"
                if key not in by_signal:
                    by_signal[key] = {"wins": 0, "losses": 0, "scratches": 0, "total": 0}
                by_signal[key]["total"] += 1
                if outcome == "win":
                    by_signal[key]["wins"] += 1
                elif outcome == "loss":
                    by_signal[key]["losses"] += 1
                else:
                    by_signal[key]["scratches"] += 1

            # By trend
            trend = pick.get("trend", "unknown")
            if trend not in by_trend:
                by_trend[trend] = {"wins": 0, "losses": 0, "scratches": 0, "total": 0}
            by_trend[trend]["total"] += 1
            if outcome == "win":
                by_trend[trend]["wins"] += 1
            elif outcome == "loss":
                by_trend[trend]["losses"] += 1
            else:
                by_trend[trend]["scratches"] += 1

    total = total_wins + total_losses + total_scratches
    win_rate = round(total_wins / total * 100, 1) if total > 0 else 0
    avg_r = round(sum(r_multiples) / len(r_multiples), 2) if r_multiples else 0

    # Compute win rates for by_signal and by_trend
    for group in (by_signal, by_trend):
        for key, stats in group.items():
            t = stats["wins"] + stats["losses"] + stats["scratches"]
            stats["win_rate"] = round(stats["wins"] / t * 100, 1) if t > 0 else 0

    # Best and worst picks
    sorted_picks = sorted(all_picks, key=lambda p: p.get("r_multiple", 0), reverse=True)
    best_picks = sorted_picks[:5]
    worst_picks = sorted_picks[-5:][::-1] if len(sorted_picks) >= 5 else sorted_picks[::-1]

    return {
        "days": days,
        "total_picks": total,
        "graded_snapshots": len(timeline),
        "wins": total_wins,
        "losses": total_losses,
        "scratches": total_scratches,
        "ambiguous": total_ambiguous,
        "win_rate": win_rate,
        "avg_r_multiple": avg_r,
        "by_signal": by_signal,
        "by_trend": by_trend,
        "best_picks": best_picks,
        "worst_picks": worst_picks,
        "timeline": sorted(timeline, key=lambda t: t["date"]),
    }
