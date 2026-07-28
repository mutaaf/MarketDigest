"""Trading API routes — paper trading and trade management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/trading", tags=["trading"])


class PaperTradeRequest(BaseModel):
    signal_id: str = ""
    symbol: str = ""
    direction: str = "BUY"
    entry_price: float = 0.0
    stop_loss: float = 0.0
    target_1: float = 0.0
    asset_type: str = "forex"


class CloseTradeRequest(BaseModel):
    trade_id: str
    exit_price: float
    reason: str = "manual"


@router.get("/paper/portfolio")
async def get_paper_portfolio():
    """Get paper trading portfolio state."""
    from src.trading.paper_engine import get_paper_portfolio
    return get_paper_portfolio()


@router.get("/paper/journal")
async def get_trade_journal(limit: int = 50):
    """Get paper trade journal."""
    from src.trading.paper_engine import get_trade_journal
    return {"trades": get_trade_journal(limit=limit)}


@router.post("/paper/enter")
async def paper_enter(req: PaperTradeRequest):
    """Enter a paper trade from a signal."""
    import yaml
    from pathlib import Path
    from src.signals.models import Signal, PositionSize

    # Build a signal object from the request
    risk = abs(req.entry_price - req.stop_loss)
    reward = abs(req.target_1 - req.entry_price)
    rr = reward / risk if risk > 0 else 0

    if rr < 2.0:
        raise HTTPException(status_code=400, detail=f"R/R {rr:.1f} is below 2:1 minimum")

    # Use risk config to determine proper dollar risk
    risk_path = Path(__file__).parent.parent.parent / "config" / "risk.yaml"
    with open(risk_path) as f:
        risk_config = yaml.safe_load(f)

    asset_key = "forex" if req.asset_type == "forex" else "options"
    acct_config = risk_config.get(asset_key, {})
    balance = acct_config.get("account_balance", 500.0)
    max_risk_pct = acct_config.get("max_risk_per_trade_pct", 2.0)
    max_dollar_risk = balance * (max_risk_pct / 100)

    # Dollar risk is capped at max per trade
    dollar_risk = min(max_dollar_risk, max_dollar_risk)  # Always use the max allowed
    dollar_reward = dollar_risk * rr

    signal = Signal(
        id=req.signal_id or "",
        symbol=req.symbol,
        name=req.symbol,
        asset_type=req.asset_type,
        direction=req.direction,
        entry_price=req.entry_price,
        stop_loss=req.stop_loss,
        target_1=req.target_1,
        target_2=req.target_1 + (req.target_1 - req.entry_price) * 0.5,
        risk_reward=round(rr, 2),
        position_size=PositionSize(
            units=1,
            dollar_risk=round(dollar_risk, 2),
            dollar_reward=round(dollar_reward, 2),
            label="1 unit",
        ),
    )

    from src.trading.paper_engine import paper_enter_trade
    result = paper_enter_trade(signal)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/paper/close")
async def paper_close(req: CloseTradeRequest):
    """Close a paper trade."""
    from src.trading.paper_engine import paper_close_trade
    result = paper_close_trade(req.trade_id, req.exit_price, req.reason)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@router.get("/paper/positions")
async def get_positions_with_prices():
    """Get open paper positions with current market prices and unrealized P&L."""
    import yfinance as yf
    from src.trading.paper_engine import get_paper_portfolio

    portfolio = get_paper_portfolio()
    all_positions = []

    for asset_key in ("forex", "options"):
        for trade in portfolio.get(asset_key, {}).get("open_trades", []):
            all_positions.append({**trade, "account": asset_key})

    if not all_positions:
        return {"positions": [], "total_unrealized_pnl": 0}

    # Build yfinance ticker map from signals config
    import yaml
    from pathlib import Path
    config_path = Path(__file__).parent.parent.parent / "config" / "signals.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    ticker_map = {}
    for group in config.get("signal_instruments", {}).values():
        for inst in group:
            ticker_map[inst["symbol"]] = inst.get("yfinance", inst["symbol"])

    # Fetch current prices
    symbols_needed = list(set(ticker_map.get(p["symbol"], p["symbol"]) for p in all_positions))
    current_prices = {}
    try:
        for yf_sym in symbols_needed:
            t = yf.Ticker(yf_sym)
            info = t.fast_info
            price = getattr(info, 'last_price', None) or getattr(info, 'previous_close', None)
            if price:
                current_prices[yf_sym] = float(price)
    except Exception:
        pass

    # Enrich positions with current price and P&L
    total_unrealized = 0
    enriched = []
    for pos in all_positions:
        yf_sym = ticker_map.get(pos["symbol"], pos["symbol"])
        current_price = current_prices.get(yf_sym)

        entry = pos["entry_price"]
        stop = pos["stop_loss"]
        target = pos["target_1"]
        direction = pos["direction"]
        dollar_risk = pos.get("dollar_risk", 10)
        risk_distance = abs(entry - stop)

        if current_price and risk_distance > 0:
            if direction == "BUY":
                price_move = current_price - entry
            else:
                price_move = entry - current_price

            r_multiple = price_move / risk_distance
            unrealized_pnl = dollar_risk * r_multiple

            # How close to stop vs target (0% = at entry, -100% = at stop, +100% = at target 1)
            target_distance = abs(target - entry)
            if target_distance > 0:
                progress_pct = (price_move / target_distance) * 100
            else:
                progress_pct = 0
        else:
            current_price = entry
            unrealized_pnl = 0
            r_multiple = 0
            progress_pct = 0

        total_unrealized += unrealized_pnl

        enriched.append({
            **pos,
            "current_price": round(current_price, 5) if current_price else None,
            "unrealized_pnl": round(unrealized_pnl, 2),
            "r_multiple": round(r_multiple, 2),
            "progress_pct": round(progress_pct, 1),
            "hit_stop": (direction == "BUY" and current_price and current_price <= stop) or
                        (direction == "SELL" and current_price and current_price >= stop),
            "hit_target": (direction == "BUY" and current_price and current_price >= target) or
                          (direction == "SELL" and current_price and current_price <= target),
        })

    return {
        "positions": enriched,
        "total_unrealized_pnl": round(total_unrealized, 2),
    }


@router.post("/paper/close-at-market")
async def close_at_market(trade_id: str):
    """Close a paper trade at current market price."""
    import yfinance as yf
    from src.trading.paper_engine import get_paper_portfolio, paper_close_trade

    # Find the trade
    portfolio = get_paper_portfolio()
    trade = None
    for asset_key in ("forex", "options"):
        for t in portfolio.get(asset_key, {}).get("open_trades", []):
            if t["id"] == trade_id:
                trade = t
                break

    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    # Get current price
    import yaml
    from pathlib import Path
    config_path = Path(__file__).parent.parent.parent / "config" / "signals.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    ticker_map = {}
    for group in config.get("signal_instruments", {}).values():
        for inst in group:
            ticker_map[inst["symbol"]] = inst.get("yfinance", inst["symbol"])

    yf_sym = ticker_map.get(trade["symbol"], trade["symbol"])
    try:
        t = yf.Ticker(yf_sym)
        info = t.fast_info
        current_price = float(getattr(info, 'last_price', None) or getattr(info, 'previous_close', trade["entry_price"]))
    except Exception:
        current_price = trade["entry_price"]

    result = paper_close_trade(trade_id, current_price, "manual")
    return result


@router.post("/paper/reset")
async def paper_reset():
    """Reset paper portfolio to initial state."""
    from src.trading.paper_engine import reset_paper_portfolio
    return reset_paper_portfolio()


@router.post("/paper/auto-trade")
async def auto_trade_signals():
    """Auto paper-trade the latest signals."""
    from src.signals.engine import scan_signals
    from src.trading.paper_engine import paper_enter_trade

    signals = scan_signals()
    results = []
    for signal in signals:
        result = paper_enter_trade(signal)
        results.append(result)
    return {"traded": len(results), "results": results}
