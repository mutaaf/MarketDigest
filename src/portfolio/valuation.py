"""Portfolio valuation — current prices, gain/loss, day change.

Partial results by design: symbols that fail to price are reported in
`warnings` and the rest of the portfolio still values.
"""

from src.fetchers.yfinance_fetcher import YFinanceFetcher

_fetcher = YFinanceFetcher()


def value_portfolio(portfolio: dict) -> dict:
    holdings = portfolio.get("holdings", [])
    cash = float(portfolio.get("cash", 0) or 0)
    symbols = [h["symbol"] for h in holdings]

    prices = _fetcher.get_batch_prices(symbols) if symbols else {}

    valued, warnings = [], []
    total_value = 0.0
    total_cost = 0.0
    total_day_change = 0.0

    for h in holdings:
        sym = h["symbol"]
        shares = float(h.get("shares", 0))
        cost_basis = float(h.get("cost_basis", 0))
        p = prices.get(sym)
        if not p:
            warnings.append(f"Couldn't get a current price for {sym} — it's shown without today's value.")
            valued.append({**h, "price": None, "value": None, "day_change_pct": None,
                           "gain": None, "gain_pct": None})
            continue

        price = p["price"]
        value = shares * price
        cost_total = shares * cost_basis
        gain = value - cost_total if cost_basis > 0 else None
        gain_pct = (gain / cost_total * 100) if gain is not None and cost_total > 0 else None
        day_change = shares * p.get("change", 0)

        total_value += value
        total_cost += cost_total
        total_day_change += day_change

        valued.append({
            **h,
            "price": round(price, 2),
            "value": round(value, 2),
            "day_change_pct": p.get("change_pct"),
            "day_change": round(day_change, 2),
            "gain": round(gain, 2) if gain is not None else None,
            "gain_pct": round(gain_pct, 2) if gain_pct is not None else None,
        })

    total_gain = total_value - total_cost if total_cost > 0 else None
    return {
        "holdings": valued,
        "cash": round(cash, 2),
        "total_value": round(total_value + cash, 2),
        "invested_value": round(total_value, 2),
        "total_cost": round(total_cost, 2) if total_cost > 0 else None,
        "total_gain": round(total_gain, 2) if total_gain is not None else None,
        "total_gain_pct": round(total_gain / total_cost * 100, 2) if total_gain is not None and total_cost > 0 else None,
        "day_change": round(total_day_change, 2),
        "day_change_pct": round(total_day_change / total_value * 100, 2) if total_value > 0 else 0.0,
        "warnings": warnings,
    }
