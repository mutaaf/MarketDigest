"""Compass portfolio API — holdings CRUD, CSV import, summary, health, recommendations."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class CreatePortfolio(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class HoldingUpsert(BaseModel):
    symbol: str = Field(min_length=1, max_length=10)
    shares: float = Field(gt=0)
    cost_basis: float = Field(ge=0, default=0)
    account: str = ""


class CashUpdate(BaseModel):
    amount: float = Field(ge=0)


class CsvImport(BaseModel):
    csv: str = Field(min_length=1)


class TargetsUpdate(BaseModel):
    targets: dict[str, float]


def _load_or_404(name: str) -> dict:
    from src.portfolio.store import load_portfolio
    data = load_portfolio(name)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No portfolio named '{name}' found.")
    return data


@router.get("/list")
async def list_all():
    from src.portfolio.store import list_portfolios
    return {"portfolios": list_portfolios()}


@router.post("/create")
async def create(body: CreatePortfolio):
    from src.portfolio.store import create_portfolio
    try:
        return create_portfolio(body.name)
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/{name}")
async def delete(name: str):
    from src.portfolio.store import delete_portfolio
    _load_or_404(name)
    delete_portfolio(name)
    return {"ok": True}


@router.get("/{name}/summary")
async def summary(name: str):
    """Everything the portfolio page needs in one call: holdings valued,
    allocation breakdowns, and health check. Partial data comes with warnings."""
    from src.portfolio.analyzer import analyze_allocation
    from src.portfolio.health import assess_health
    from src.portfolio.overlap import analyze_overlap
    from src.portfolio.valuation import value_portfolio

    portfolio = _load_or_404(name)
    valuation = value_portfolio(portfolio)
    allocation = analyze_allocation(valuation)
    health = assess_health(allocation, valuation)
    return {
        "name": portfolio["name"],
        "valuation": valuation,
        "allocation": allocation,
        "health": health,
        "overlap": analyze_overlap(allocation),
        "targets": portfolio.get("targets") or {},
    }


@router.get("/{name}/history")
async def history(name: str):
    from src.portfolio.history import get_history
    _load_or_404(name)
    return {"history": get_history(name)}


@router.post("/{name}/holding")
async def upsert(name: str, body: HoldingUpsert):
    from src.portfolio.store import upsert_holding
    _load_or_404(name)
    return upsert_holding(name, body.symbol, body.shares, body.cost_basis, body.account)


@router.delete("/{name}/holding/{symbol}")
async def remove(name: str, symbol: str):
    from src.portfolio.store import delete_holding
    _load_or_404(name)
    return delete_holding(name, symbol)


@router.put("/{name}/cash")
async def cash(name: str, body: CashUpdate):
    from src.portfolio.store import set_cash
    _load_or_404(name)
    return set_cash(name, body.amount)


@router.put("/{name}/targets")
async def targets(name: str, body: TargetsUpdate):
    from src.portfolio.store import save_portfolio
    data = _load_or_404(name)
    total = sum(body.targets.values())
    if body.targets and abs(total - 100) > 0.5:
        raise HTTPException(status_code=422,
                            detail=f"Targets should add up to 100% (they add up to {total:.0f}%).")
    data["targets"] = {k: round(v, 1) for k, v in body.targets.items()}
    return save_portfolio(data)


class HoldingsImport(BaseModel):
    holdings: list[HoldingUpsert] = Field(min_length=1, max_length=200)


@router.post("/{name}/import-holdings")
async def import_bulk(name: str, body: HoldingsImport):
    """Bulk import (used by the review step of smart import)."""
    from src.portfolio.store import import_holdings
    _load_or_404(name)
    rows = [{"symbol": h.symbol.strip().upper(), "shares": round(h.shares, 6),
             "cost_basis": round(h.cost_basis, 4), "account": h.account.strip()}
            for h in body.holdings]
    import_holdings(name, rows)
    return {"imported": len(rows)}


@router.post("/{name}/import-csv")
async def import_csv(name: str, body: CsvImport):
    from src.portfolio.store import import_holdings, parse_csv
    _load_or_404(name)
    holdings, skipped = parse_csv(body.csv)
    if not holdings:
        raise HTTPException(status_code=422, detail=skipped[0] if skipped else
                            "No holdings could be read from that file.")
    import_holdings(name, holdings)
    return {"imported": len(holdings), "skipped": skipped}


@router.get("/{name}/recommendations")
async def recommendations(name: str):
    """Ranked 'what should I buy next' picks. First run fetches fund data and
    can take ~30s; results are cached for subsequent calls."""
    from src.portfolio.analyzer import analyze_allocation
    from src.portfolio.recommender import recommend
    from src.portfolio.valuation import value_portfolio

    portfolio = _load_or_404(name)
    valuation = value_portfolio(portfolio)
    allocation = analyze_allocation(valuation)
    return recommend(portfolio, valuation, allocation)


class WatchlistAdd(BaseModel):
    symbol: str = Field(min_length=1, max_length=10)
    buy_price: float | None = Field(default=None, gt=0)
    notes: str = ""


class RetirementInputs(BaseModel):
    current_age: int = Field(ge=16, le=90)
    retire_age: int = Field(ge=30, le=90)
    current_assets: float = Field(ge=0)
    monthly_contribution: float = Field(ge=0)
    expected_return_pct: float = Field(default=7.0, ge=0, le=15)
    inflation_pct: float = Field(default=2.5, ge=0, le=10)
    monthly_spending: float | None = Field(default=None, ge=0)


@router.get("/{name}/watchlist")
async def get_watchlist(name: str):
    from src.portfolio.watchlist import enrich_watchlist
    _load_or_404(name)
    return enrich_watchlist(name)


@router.post("/{name}/watchlist")
async def add_watch(name: str, body: WatchlistAdd):
    from src.portfolio.watchlist import add_item
    _load_or_404(name)
    add_item(name, body.symbol, body.buy_price, body.notes)
    return {"ok": True}


@router.delete("/{name}/watchlist/{symbol}")
async def remove_watch(name: str, symbol: str):
    from src.portfolio.watchlist import remove_item
    _load_or_404(name)
    remove_item(name, symbol)
    return {"ok": True}


@router.get("/{name}/retirement")
async def get_retirement(name: str):
    """Saved retirement plan (inputs + projection), with assets prefilled
    from the portfolio when no plan is saved yet."""
    from src.portfolio.retirement import project
    from src.portfolio.valuation import value_portfolio

    portfolio = _load_or_404(name)
    saved = portfolio.get("retirement")
    if not saved:
        valuation = value_portfolio(portfolio)
        return {"inputs": {"current_assets": valuation["total_value"]}, "projection": None}
    return {"inputs": saved, "projection": project(**saved)}


@router.post("/{name}/retirement")
async def save_retirement(name: str, body: RetirementInputs):
    from src.portfolio.retirement import project
    from src.portfolio.store import save_portfolio

    if body.retire_age <= body.current_age:
        raise HTTPException(status_code=422,
                            detail="Retirement age needs to be after your current age.")
    portfolio = _load_or_404(name)
    inputs = body.model_dump()
    portfolio["retirement"] = inputs
    save_portfolio(portfolio)
    return {"inputs": inputs, "projection": project(**inputs)}


# ── Comparison + symbol search (portfolio-independent) ──────────

compass_router = APIRouter(prefix="/api/compass", tags=["compass"])


class ExtractRequest(BaseModel):
    image_base64: str | None = Field(default=None, max_length=14_000_000)  # ~10MB image
    media_type: str = "image/png"
    text: str | None = Field(default=None, max_length=50_000)


@compass_router.post("/extract-holdings")
async def extract_holdings(body: ExtractRequest):
    """Read holdings from a brokerage screenshot or pasted text. Returns
    candidates for user review — nothing is saved by this endpoint."""
    from src.portfolio.extract import extract_from_image, extract_from_text

    if body.image_base64:
        if body.media_type not in ("image/png", "image/jpeg", "image/webp", "image/gif"):
            raise HTTPException(status_code=422, detail="That image type isn't supported — "
                                                        "use a PNG or JPEG screenshot.")
        return extract_from_image(body.image_base64, body.media_type)
    if body.text and body.text.strip():
        return extract_from_text(body.text)
    raise HTTPException(status_code=422, detail="Send a screenshot or some copied text.")


@compass_router.get("/compare")
async def compare_symbols(a: str, b: str):
    from src.portfolio.compare import compare
    result = compare(a, b)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return result


@compass_router.get("/search")
async def search(q: str = ""):
    """Symbol/name autocomplete over the Compass universe (stocks + ETFs)."""
    from config.settings import get_compass_universe
    q = q.strip().upper()
    out = []
    for item in get_compass_universe():
        if not q or q in item["symbol"] or q in item.get("name", "").upper():
            out.append({"symbol": item["symbol"], "name": item.get("name"),
                        "type": item["instrument_type"],
                        "asset_class": item.get("asset_class"),
                        "category": item.get("category")})
    return {"results": out[:20]}
