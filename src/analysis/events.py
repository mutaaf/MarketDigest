"""Static reference data and helpers for market events, earnings, and FOMC calendar."""

from datetime import date, datetime
from src.utils.timezone import now_ct


# ── FOMC Meeting Dates (updated annually from federalreserve.gov) ──────

FOMC_DATES: list[date] = [
    # 2025
    date(2025, 1, 29),
    date(2025, 3, 19),
    date(2025, 5, 7),
    date(2025, 6, 18),
    date(2025, 7, 30),
    date(2025, 9, 17),
    date(2025, 10, 29),
    date(2025, 12, 17),
    # 2026
    date(2026, 1, 28),
    date(2026, 3, 18),
    date(2026, 4, 29),
    date(2026, 6, 17),
    date(2026, 7, 29),
    date(2026, 9, 16),
    date(2026, 10, 28),
    date(2026, 12, 16),
]


# ── Bellwether Symbols (~50 high-impact earnings tickers) ──────────────

BELLWETHER_SYMBOLS: set[str] = {
    # Mega-cap tech
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA",
    # Semiconductors
    "AVGO", "AMD", "INTC", "QCOM", "MU",
    # Financials
    "JPM", "BAC", "GS", "MS", "WFC", "C", "BLK",
    # Healthcare
    "UNH", "JNJ", "PFE", "ABBV", "LLY", "MRK",
    # Consumer
    "WMT", "HD", "COST", "NKE", "MCD", "SBUX", "DIS",
    # Industrials
    "CAT", "BA", "UPS", "FDX", "DE",
    # Energy
    "XOM", "CVX", "COP",
    # Communication
    "NFLX", "CRM", "ADBE",
    # Other high-impact
    "V", "MA", "PYPL", "SQ", "COIN",
}


# ── Event Context — "why it matters" for major economic releases ────────

EVENT_CONTEXT: dict[str, str] = {
    "nonfarm payrolls": "Monthly jobs report — drives Fed rate expectations",
    "non-farm payrolls": "Monthly jobs report — drives Fed rate expectations",
    "unemployment rate": "Labor market health gauge — Fed dual mandate indicator",
    "cpi": "Consumer inflation — key input for Fed rate decisions",
    "consumer price index": "Consumer inflation — key input for Fed rate decisions",
    "core cpi": "Inflation excluding food/energy — Fed's preferred CPI measure",
    "pce": "Personal consumption — the Fed's preferred inflation gauge",
    "core pce": "Inflation excluding food/energy — Fed's top inflation metric",
    "ppi": "Producer prices — signals future consumer inflation direction",
    "producer price index": "Producer prices — signals future consumer inflation direction",
    "retail sales": "Consumer spending health — 70% of US GDP is consumption",
    "gdp": "Broadest measure of economic growth",
    "ism manufacturing": "Factory activity — readings above 50 signal expansion",
    "ism services": "Services sector health — largest part of the US economy",
    "ism non-manufacturing": "Services sector health — largest part of the US economy",
    "fomc": "Fed sets interest rate direction for the economy",
    "federal funds rate": "Fed sets interest rate direction for the economy",
    "fed interest rate": "Fed sets interest rate direction for the economy",
    "initial jobless claims": "Weekly layoff pulse — early recession warning signal",
    "jolts": "Job openings — measures labor demand vs supply",
    "consumer confidence": "Household spending outlook — leads retail sales trends",
    "michigan consumer": "Consumer inflation expectations — watched closely by the Fed",
    "housing starts": "New construction — sensitive to mortgage rates and demand",
    "existing home sales": "Housing market health — reflects consumer confidence and rates",
    "durable goods": "Business investment proxy — signals economic momentum",
    "industrial production": "Factory and utility output — cyclical economic barometer",
    "trade balance": "Net exports — affects GDP and dollar strength",
    "treasury budget": "Federal deficit/surplus — impacts bond supply and yields",
}


def get_event_context(event_name: str) -> str | None:
    """Look up a 1-line 'why it matters' explanation for an economic event.

    Uses case-insensitive substring matching against EVENT_CONTEXT keys.
    """
    lower = event_name.lower()
    for pattern, explanation in EVENT_CONTEXT.items():
        if pattern in lower:
            return explanation
    return None


def get_next_fomc_date() -> tuple[date, int] | None:
    """Return (next_fomc_date, days_until) or None if no future dates."""
    today = now_ct().date()
    for d in FOMC_DATES:
        if d >= today:
            return d, (d - today).days
    return None


def get_forward_calendar() -> list[dict]:
    """Build a forward-looking calendar with countdowns to key events.

    Returns list of {event, date, days_until, formatted}.
    """
    today = now_ct().date()
    items = []

    # FOMC countdown
    fomc = get_next_fomc_date()
    if fomc:
        fomc_date, days = fomc
        items.append({
            "event": "FOMC Rate Decision",
            "date": fomc_date.isoformat(),
            "days_until": days,
            "formatted": f"{fomc_date.strftime('%b %d')} ({days} day{'s' if days != 1 else ''})",
        })

    return items


def classify_earnings(earnings: list[dict]) -> tuple[list[dict], list[dict], int]:
    """Split earnings into (bellwether_list, other_list, total_count).

    Each earning dict should have at least a 'symbol' key.
    """
    bellwether = []
    other = []
    for e in earnings:
        sym = (e.get("symbol") or "").upper()
        if sym in BELLWETHER_SYMBOLS:
            bellwether.append(e)
        else:
            other.append(e)
    return bellwether, other, len(earnings)
