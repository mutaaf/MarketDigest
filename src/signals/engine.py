"""Signal engine — orchestrates signal scanning, backtesting, and signal history."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yaml
import yfinance as yf

from src.signals.forex_signals import generate_forex_signals
from src.signals.models import Signal
from src.signals.options_signals import generate_options_signals
from src.utils.logging_config import get_logger

logger = get_logger("signal_engine")

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "signals.yaml"
RISK_PATH = Path(__file__).parent.parent.parent / "config" / "risk.yaml"
SIGNALS_LOG = Path(__file__).parent.parent.parent / "logs" / "signals"


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _load_risk() -> dict:
    with open(RISK_PATH) as f:
        return yaml.safe_load(f)


def _ensure_log_dir():
    SIGNALS_LOG.mkdir(parents=True, exist_ok=True)


def _fetch_ohlcv(yf_ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame | None:
    """Fetch OHLCV data via yfinance."""
    try:
        ticker = yf.Ticker(yf_ticker)
        df = ticker.history(period=period, interval=interval)
        if df is None or df.empty or len(df) < 20:
            return None
        return df
    except Exception as e:
        logger.error(f"Failed to fetch {yf_ticker}: {e}")
        return None


def scan_signals() -> list[Signal]:
    """Run a full signal scan across all configured instruments.

    Returns list of signals that passed both confluence and 2:1 R/R filters.
    """
    config = _load_config()
    all_signals = []

    # Scan forex instruments
    for instrument in config.get("signal_instruments", {}).get("forex", []):
        yf_ticker = instrument.get("yfinance")
        if not yf_ticker:
            continue
        df = _fetch_ohlcv(yf_ticker, period="6mo")
        if df is None:
            continue
        try:
            signals = generate_forex_signals(df, instrument)
            all_signals.extend(signals)
        except Exception as e:
            logger.error(f"Forex signal error for {instrument['symbol']}: {e}")

    # Scan options instruments
    for instrument in config.get("signal_instruments", {}).get("options", []):
        yf_ticker = instrument.get("yfinance")
        if not yf_ticker:
            continue
        df = _fetch_ohlcv(yf_ticker, period="1y")  # Need more data for IV rank
        if df is None:
            continue
        try:
            signals = generate_options_signals(df, instrument)
            all_signals.extend(signals)
        except Exception as e:
            logger.error(f"Options signal error for {instrument['symbol']}: {e}")

    # Sort by confluence score descending
    all_signals.sort(key=lambda s: s.confluence_score, reverse=True)

    # Auto-generate AI insights for high-confidence signals
    if all_signals:
        _generate_ai_insights(all_signals)

    # Save to signal log (with AI explanations)
    if all_signals:
        _save_signals(all_signals)

    logger.info(f"Scan complete: {len(all_signals)} signals generated")
    return all_signals


def _generate_ai_insights(signals: list[Signal]):
    """Auto-generate AI insights for TAKE-rated signals and cache them."""
    from src.signals.ai_cache import generate_and_cache_insight, get_cached_explanation, is_fresh
    from src.signals.autopilot import rate_signal

    # Fetch market context once for all signals
    market_context = None
    try:
        from ui.routes.signals import _fetch_market_context
        market_context = _fetch_market_context("")
    except Exception:
        pass

    generated = 0
    for signal in signals:
        # Only auto-generate for TAKE and WATCH signals
        rating = rate_signal(signal)
        if rating == "SKIP":
            continue

        # Check if already cached and fresh
        if is_fresh(signal.id):
            signal.explanation = get_cached_explanation(signal.id)
            continue

        # Generate and cache
        explanation = generate_and_cache_insight(signal.to_dict(), market_context)
        if explanation:
            signal.explanation = explanation
            generated += 1

        # Limit to 5 AI calls per scan to avoid rate limits
        if generated >= 5:
            break

    if generated:
        logger.info(f"Generated {generated} AI insights during scan")


def _save_signals(signals: list[Signal]):
    """Save signals to JSON log file (with AI explanations)."""
    _ensure_log_dir()
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H%M%S")
    filepath = SIGNALS_LOG / f"{date_str}_{time_str}.json"

    signal_dicts = []
    for s in signals:
        d = s.to_dict()
        if s.explanation:
            d["ai_explanation"] = s.explanation
        signal_dicts.append(d)

    data = {
        "timestamp": datetime.now().isoformat(),
        "count": len(signals),
        "signals": signal_dicts,
    }
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)


def load_signal_history(days: int = 7) -> list[dict]:
    """Load signal history from the past N days."""
    _ensure_log_dir()
    cutoff = datetime.now() - timedelta(days=days)
    all_signals = []

    for filepath in sorted(SIGNALS_LOG.glob("*.json"), reverse=True):
        try:
            date_str = filepath.stem.split("_")[0]
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date < cutoff:
                break
            with open(filepath) as f:
                data = json.load(f)
            all_signals.extend(data.get("signals", []))
        except Exception:
            continue

    return all_signals


def get_latest_signals() -> list[dict]:
    """Get the most recent scan's signals, enriched with cached AI insights."""
    _ensure_log_dir()
    files = sorted(SIGNALS_LOG.glob("*.json"), reverse=True)
    if not files:
        return []
    try:
        with open(files[0]) as f:
            data = json.load(f)
        signals = data.get("signals", [])

        # Enrich with cached AI insights
        from src.signals.ai_cache import enrich_signals_with_insights
        signals = enrich_signals_with_insights(signals)

        return signals
    except Exception:
        return []


# ── Backtesting ──────────────────────────────────────────────────────────────


def backtest_strategy(
    yf_ticker: str,
    asset_type: str = "forex",
    instrument: dict | None = None,
    lookback_months: int = 6,
    start_balance: float = 500.0,
) -> dict:
    """Backtest a signal strategy on historical data.

    Walks through historical data day by day, generating signals and
    simulating trades with 2:1 R/R targets.

    Returns dict with metrics: win_rate, total_trades, profit_factor,
    max_drawdown, equity_curve, trades list.
    """
    # Fetch historical data
    period = f"{lookback_months + 3}mo"  # Extra for indicator warmup
    df = _fetch_ohlcv(yf_ticker, period=period, interval="1d")
    if df is None or len(df) < 100:
        return {"error": "Insufficient data", "trades": []}

    config = _load_config()
    if instrument is None:
        instrument = {"symbol": yf_ticker, "yfinance": yf_ticker, "name": yf_ticker,
                      "pip_size": 0.01, "pip_value_per_micro_lot": 0.07}

    warmup = 60  # Need 60 bars for indicator warmup
    trades = []
    equity = start_balance
    peak_equity = equity
    max_drawdown = 0.0
    equity_curve = []

    # Walk through data day by day
    i = warmup
    in_trade = False
    trade_entry = None
    trade_direction = None
    trade_stop = None
    trade_target = None
    trade_risk_dollars = None

    risk_config = _load_risk().get(asset_type, {})
    max_risk_pct = risk_config.get("max_risk_per_trade_pct", 2.0)

    while i < len(df):
        current_slice = df.iloc[:i + 1]
        high = float(current_slice["High"].iloc[-1])
        low = float(current_slice["Low"].iloc[-1])
        date = current_slice.index[-1]

        if in_trade:
            # Check if stop or target hit
            if trade_direction == "BUY":
                if low <= trade_stop:
                    # Stopped out
                    pnl = -trade_risk_dollars
                    equity += pnl
                    trades.append({
                        "date": str(date.date()),
                        "direction": trade_direction,
                        "entry": trade_entry,
                        "exit": trade_stop,
                        "target": trade_target,
                        "stop": trade_stop,
                        "pnl": round(pnl, 2),
                        "outcome": "loss",
                        "r_multiple": -1.0,
                    })
                    in_trade = False
                elif high >= trade_target:
                    # Hit target (2R)
                    pnl = trade_risk_dollars * 2
                    equity += pnl
                    trades.append({
                        "date": str(date.date()),
                        "direction": trade_direction,
                        "entry": trade_entry,
                        "exit": trade_target,
                        "target": trade_target,
                        "stop": trade_stop,
                        "pnl": round(pnl, 2),
                        "outcome": "win",
                        "r_multiple": 2.0,
                    })
                    in_trade = False
            else:  # SELL
                if high >= trade_stop:
                    pnl = -trade_risk_dollars
                    equity += pnl
                    trades.append({
                        "date": str(date.date()),
                        "direction": trade_direction,
                        "entry": trade_entry,
                        "exit": trade_stop,
                        "target": trade_target,
                        "stop": trade_stop,
                        "pnl": round(pnl, 2),
                        "outcome": "loss",
                        "r_multiple": -1.0,
                    })
                    in_trade = False
                elif low <= trade_target:
                    pnl = trade_risk_dollars * 2
                    equity += pnl
                    trades.append({
                        "date": str(date.date()),
                        "direction": trade_direction,
                        "entry": trade_entry,
                        "exit": trade_target,
                        "target": trade_target,
                        "stop": trade_stop,
                        "pnl": round(pnl, 2),
                        "outcome": "win",
                        "r_multiple": 2.0,
                    })
                    in_trade = False

        if not in_trade:
            # Try to generate a signal
            try:
                if asset_type == "forex":
                    signals = generate_forex_signals(current_slice, instrument)
                else:
                    signals = generate_options_signals(current_slice, instrument)

                if signals:
                    sig = signals[0]
                    trade_entry = sig.entry_price
                    trade_direction = sig.direction
                    trade_stop = sig.stop_loss
                    trade_target = sig.target_1
                    trade_risk_dollars = equity * (max_risk_pct / 100)
                    in_trade = True
            except Exception:
                pass

        # Track equity
        peak_equity = max(peak_equity, equity)
        dd = (peak_equity - equity) / peak_equity * 100 if peak_equity > 0 else 0
        max_drawdown = max(max_drawdown, dd)
        equity_curve.append({"date": str(date.date()), "equity": round(equity, 2)})

        i += 1

    # Compute metrics
    wins = [t for t in trades if t["outcome"] == "win"]
    losses = [t for t in trades if t["outcome"] == "loss"]
    total = len(trades)
    win_rate = len(wins) / total * 100 if total > 0 else 0

    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    avg_r = sum(t["r_multiple"] for t in trades) / total if total > 0 else 0

    # Check if strategy passes the gate
    gate = config.get("backtest_gate", {})
    passes_gate = (
        total >= gate.get("min_trades", 50)
        and win_rate >= gate.get("min_win_rate", 50.0)
    )

    return {
        "symbol": instrument.get("symbol", yf_ticker),
        "asset_type": asset_type,
        "lookback_months": lookback_months,
        "start_balance": start_balance,
        "final_balance": round(equity, 2),
        "total_return_pct": round((equity - start_balance) / start_balance * 100, 1),
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 1),
        "avg_r_multiple": round(avg_r, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else "inf",
        "max_drawdown_pct": round(max_drawdown, 1),
        "passes_gate": passes_gate,
        "gate_requirements": gate,
        "equity_curve": equity_curve,
        "trades": trades,
    }
