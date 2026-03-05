"""Financial statement analysis — fetch fundamentals and score them."""

from src.cache.manager import CacheManager
from src.utils.logging_config import get_logger

logger = get_logger("fundamentals")

_cache = CacheManager()
_CACHE_TTL = 6 * 60 * 60  # 6 hours


def is_equity_symbol(category: str) -> bool:
    """True for US stocks only."""
    return category == "us_stock"


def fetch_fundamentals(symbol: str, yf_symbol: str) -> dict | None:
    """Fetch fundamental data via yfinance (primary) with Finnhub fallback.

    Returns:
        dict with 'metrics' and 'highlights' keys, or None on failure.
    """
    cache_key = f"fundamentals:{symbol}"
    cached = _cache.get(cache_key, max_age_seconds=_CACHE_TTL)
    if cached is not None:
        return cached

    data = _fetch_yfinance(yf_symbol)
    if data is None:
        data = _fetch_finnhub(symbol)

    if data is not None:
        _cache.set(cache_key, data)

    return data


def _fetch_yfinance(yf_symbol: str) -> dict | None:
    """Fetch fundamentals from yfinance."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info
        if not info or not info.get("marketCap"):
            return None

        metrics = {
            "pe_ratio": _safe(info.get("trailingPE")),
            "forward_pe": _safe(info.get("forwardPE")),
            "pb_ratio": _safe(info.get("priceToBook")),
            "ev_ebitda": _safe(info.get("enterpriseToEbitda")),
            "debt_equity": _safe(info.get("debtToEquity", None), divisor=100),
            "current_ratio": _safe(info.get("currentRatio")),
            "free_cash_flow": _safe(info.get("freeCashflow")),
            "revenue_growth": _safe(info.get("revenueGrowth"), pct=True),
            "eps_growth": _safe(info.get("earningsGrowth"), pct=True),
            "gross_margin": _safe(info.get("grossMargins"), pct=True),
            "operating_margin": _safe(info.get("operatingMargins"), pct=True),
            "net_margin": _safe(info.get("profitMargins"), pct=True),
            "roe": _safe(info.get("returnOnEquity"), pct=True),
            "roa": _safe(info.get("returnOnAssets"), pct=True),
        }

        highlights = {
            "income": {
                "revenue": _safe(info.get("totalRevenue")),
                "net_income": _safe(info.get("netIncomeToCommon")),
                "eps": _safe(info.get("trailingEps")),
            },
            "balance": {
                "total_assets": _safe(info.get("totalAssets")),
                "total_debt": _safe(info.get("totalDebt")),
                "cash": _safe(info.get("totalCash")),
                "equity": _safe(info.get("bookValue")),
            },
            "cashflow": {
                "operating_cf": _safe(info.get("operatingCashflow")),
                "capex": None,  # Not directly in yfinance info
                "fcf": _safe(info.get("freeCashflow")),
            },
        }

        return {
            "metrics": metrics,
            "highlights": highlights,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
        }
    except Exception as e:
        logger.debug(f"yfinance fundamentals failed for {yf_symbol}: {e}")
        return None


def _fetch_finnhub(symbol: str) -> dict | None:
    """Fallback: fetch fundamentals from Finnhub."""
    try:
        from config.settings import get_settings
        settings = get_settings()
        api_key = settings.finnhub_key
        if not api_key:
            return None

        import requests
        url = f"https://finnhub.io/api/v1/stock/metric?symbol={symbol}&metric=all&token={api_key}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None

        data = resp.json()
        m = data.get("metric", {})
        if not m:
            return None

        metrics = {
            "pe_ratio": _safe(m.get("peNormalizedAnnual")),
            "forward_pe": _safe(m.get("peTTM")),
            "pb_ratio": _safe(m.get("pbAnnual")),
            "ev_ebitda": _safe(m.get("currentEv/ebitdaAnnual")),
            "debt_equity": _safe(m.get("totalDebt/totalEquityAnnual"), divisor=100),
            "current_ratio": _safe(m.get("currentRatioAnnual")),
            "free_cash_flow": _safe(m.get("freeCashFlowTTM")),
            "revenue_growth": _safe(m.get("revenueGrowthTTMYoy"), pct=False),
            "eps_growth": _safe(m.get("epsGrowthTTMYoy"), pct=False),
            "gross_margin": _safe(m.get("grossMarginTTM"), pct=False),
            "operating_margin": _safe(m.get("operatingMarginTTM"), pct=False),
            "net_margin": _safe(m.get("netProfitMarginTTM"), pct=False),
            "roe": _safe(m.get("roeTTM"), pct=False),
            "roa": _safe(m.get("roaTTM"), pct=False),
        }

        highlights = {
            "income": {"revenue": _safe(m.get("revenueTTM")), "net_income": None, "eps": _safe(m.get("epsTTM"))},
            "balance": {"total_assets": None, "total_debt": None, "cash": None, "equity": _safe(m.get("bookValuePerShareAnnual"))},
            "cashflow": {"operating_cf": None, "capex": None, "fcf": _safe(m.get("freeCashFlowTTM"))},
        }

        return {
            "metrics": metrics,
            "highlights": highlights,
            "sector": None,
            "industry": None,
            "market_cap": _safe(m.get("marketCapitalization"), scale=1e6),
        }
    except Exception as e:
        logger.debug(f"Finnhub fundamentals failed for {symbol}: {e}")
        return None


def _safe(val, divisor: float = 1, pct: bool = False, scale: float = 1) -> float | None:
    """Safely convert to float, handling None/NaN."""
    if val is None:
        return None
    try:
        import math
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        if divisor != 1:
            f = f / divisor
        if pct:
            f = f * 100  # yfinance returns 0.15 for 15%
        if scale != 1:
            f = f * scale
        return round(f, 4)
    except (TypeError, ValueError):
        return None


# ── Scoring thresholds ──────────────────────────────────────────


def _score_metric(value: float | None, thresholds: list[tuple[float, float]], higher_is_better: bool = True) -> float | None:
    """Score a metric 0-100 given (threshold, score) pairs sorted ascending."""
    if value is None:
        return None
    for threshold, score in (thresholds if higher_is_better else reversed(thresholds)):
        if higher_is_better and value >= threshold:
            return score
        elif not higher_is_better and value <= threshold:
            return score
    return thresholds[0][1] if higher_is_better else thresholds[-1][1]


def _score_valuation(metrics: dict) -> float | None:
    """Score valuation metrics. Lower P/E, P/B, EV/EBITDA = better."""
    scores = []

    pe = metrics.get("pe_ratio")
    if pe is not None and pe > 0:
        # Lower is better
        if pe < 15:
            scores.append(90)
        elif pe < 20:
            scores.append(70)
        elif pe < 30:
            scores.append(50)
        else:
            scores.append(30)

    pb = metrics.get("pb_ratio")
    if pb is not None and pb > 0:
        if pb < 1.5:
            scores.append(90)
        elif pb < 3:
            scores.append(70)
        elif pb < 5:
            scores.append(50)
        else:
            scores.append(30)

    ev_ebitda = metrics.get("ev_ebitda")
    if ev_ebitda is not None and ev_ebitda > 0:
        if ev_ebitda < 10:
            scores.append(90)
        elif ev_ebitda < 15:
            scores.append(70)
        elif ev_ebitda < 25:
            scores.append(50)
        else:
            scores.append(30)

    return round(sum(scores) / len(scores), 1) if scores else None


def _score_profitability(metrics: dict) -> float | None:
    """Score profitability metrics. Higher margins and returns = better."""
    scores = []

    gm = metrics.get("gross_margin")
    if gm is not None:
        if gm > 50:
            scores.append(90)
        elif gm > 30:
            scores.append(70)
        elif gm > 15:
            scores.append(50)
        else:
            scores.append(30)

    om = metrics.get("operating_margin")
    if om is not None:
        if om > 25:
            scores.append(90)
        elif om > 15:
            scores.append(70)
        elif om > 5:
            scores.append(50)
        else:
            scores.append(30)

    roe = metrics.get("roe")
    if roe is not None:
        if roe > 20:
            scores.append(90)
        elif roe > 15:
            scores.append(70)
        elif roe > 5:
            scores.append(50)
        else:
            scores.append(30)

    roa = metrics.get("roa")
    if roa is not None:
        if roa > 10:
            scores.append(90)
        elif roa > 5:
            scores.append(70)
        elif roa > 2:
            scores.append(50)
        else:
            scores.append(30)

    return round(sum(scores) / len(scores), 1) if scores else None


def _score_growth(metrics: dict) -> float | None:
    """Score growth metrics. Higher revenue/EPS growth = better."""
    scores = []

    rg = metrics.get("revenue_growth")
    if rg is not None:
        if rg > 20:
            scores.append(90)
        elif rg > 10:
            scores.append(70)
        elif rg > 0:
            scores.append(50)
        else:
            scores.append(20)

    eg = metrics.get("eps_growth")
    if eg is not None:
        if eg > 20:
            scores.append(90)
        elif eg > 10:
            scores.append(70)
        elif eg > 0:
            scores.append(50)
        else:
            scores.append(20)

    return round(sum(scores) / len(scores), 1) if scores else None


def _score_health(metrics: dict) -> float | None:
    """Score financial health. Low D/E + high current ratio = better."""
    scores = []

    de = metrics.get("debt_equity")
    if de is not None:
        if de < 0.5:
            scores.append(90)
        elif de < 1.0:
            scores.append(70)
        elif de < 2.0:
            scores.append(50)
        else:
            scores.append(25)

    cr = metrics.get("current_ratio")
    if cr is not None:
        if cr > 2.0:
            scores.append(90)
        elif cr > 1.5:
            scores.append(70)
        elif cr > 1.0:
            scores.append(50)
        else:
            scores.append(25)

    fcf = metrics.get("free_cash_flow")
    if fcf is not None:
        if fcf > 0:
            scores.append(80)
        else:
            scores.append(30)

    return round(sum(scores) / len(scores), 1) if scores else None


def score_fundamentals(fundamentals: dict) -> dict:
    """Score fundamentals across 4 dimensions, each 0-100.

    Returns:
        {valuation, profitability, growth, health, composite} — each 0-100.
        Sub-scores average available metrics (skip None).
        Composite = equal-weight of available sub-scores.
    """
    metrics = fundamentals.get("metrics", {})

    valuation = _score_valuation(metrics)
    profitability = _score_profitability(metrics)
    growth = _score_growth(metrics)
    health = _score_health(metrics)

    sub_scores = [s for s in [valuation, profitability, growth, health] if s is not None]
    composite = round(sum(sub_scores) / len(sub_scores), 1) if sub_scores else 50.0

    return {
        "valuation": valuation,
        "profitability": profitability,
        "growth": growth,
        "health": health,
        "composite": composite,
    }
