"""Instruments CRUD endpoints."""

from fastapi import APIRouter, HTTPException

from config.settings import get_settings, reload_settings, save_instruments
from ui.models import InstrumentToggle, NewInstrument

router = APIRouter(prefix="/api/instruments", tags=["instruments"])

# Map category names to YAML paths
_CATEGORY_PATHS = {
    "forex": ("forex", "majors"),
    "forex_index": ("forex", "indices"),
    "us_index": ("us_indices", "spot"),
    "us_futures": ("us_indices", "futures"),
    "metals": ("commodities", "metals"),
    "energy": ("commodities", "energy"),
    "agriculture": ("commodities", "agriculture"),
    "crypto": ("crypto", None),
}


def _get_instruments_flat(instruments: dict) -> list[dict]:
    """Flatten instruments.yaml into a list with category info."""
    flat = []
    for pair in instruments.get("forex", {}).get("majors", []):
        flat.append({**pair, "category": "forex", "subcategory": "majors"})
    for idx in instruments.get("forex", {}).get("indices", []):
        flat.append({**idx, "category": "forex_index", "subcategory": "indices"})
    for item in instruments.get("us_indices", {}).get("spot", []):
        flat.append({**item, "category": "us_index", "subcategory": "spot"})
    for item in instruments.get("us_indices", {}).get("futures", []):
        flat.append({**item, "category": "us_futures", "subcategory": "futures"})
    for sub in ["metals", "energy", "agriculture"]:
        for item in instruments.get("commodities", {}).get(sub, []):
            flat.append({**item, "category": sub, "subcategory": sub})
    for item in instruments.get("crypto", []):
        flat.append({**item, "category": "crypto", "subcategory": None})
    return flat


def _find_instrument_list(instruments: dict, category: str):
    """Return the list from instruments dict that contains the given category."""
    path = _CATEGORY_PATHS.get(category)
    if not path:
        return None

    top_key, sub_key = path
    if sub_key is None:
        return instruments.get(top_key, [])
    return instruments.get(top_key, {}).get(sub_key, [])


@router.get("")
def list_instruments():
    """Get all instruments with their enabled status."""
    settings = get_settings()
    return _get_instruments_flat(settings.instruments)


@router.put("/{category}/{symbol}/toggle")
def toggle_instrument(category: str, symbol: str, body: InstrumentToggle):
    """Enable/disable an instrument."""
    settings = get_settings()
    instruments = settings.instruments

    items = _find_instrument_list(instruments, category)
    if items is None:
        raise HTTPException(status_code=404, detail=f"Unknown category: {category}")

    for item in items:
        if item.get("symbol") == symbol:
            item["enabled"] = body.enabled
            save_instruments(instruments)
            reload_settings()
            return {"success": True, "symbol": symbol, "enabled": body.enabled}

    raise HTTPException(status_code=404, detail=f"Instrument not found: {symbol}")


@router.post("")
def add_instrument(body: NewInstrument):
    """Add a new instrument."""
    settings = get_settings()
    instruments = settings.instruments

    category = body.category
    path = _CATEGORY_PATHS.get(category)
    if not path:
        raise HTTPException(status_code=400, detail=f"Unknown category: {category}")

    top_key, sub_key = path
    new_item = {
        "symbol": body.symbol,
        "yfinance": body.yfinance,
        "name": body.name,
        "enabled": True,
    }
    if body.twelvedata:
        new_item["twelvedata"] = body.twelvedata

    if sub_key is None:
        if top_key not in instruments:
            instruments[top_key] = []
        instruments[top_key].append(new_item)
    else:
        if top_key not in instruments:
            instruments[top_key] = {}
        if sub_key not in instruments[top_key]:
            instruments[top_key][sub_key] = []
        instruments[top_key][sub_key].append(new_item)

    save_instruments(instruments)
    reload_settings()
    return {"success": True, "instrument": new_item}


@router.delete("/{category}/{symbol}")
def delete_instrument(category: str, symbol: str):
    """Delete an instrument."""
    settings = get_settings()
    instruments = settings.instruments

    items = _find_instrument_list(instruments, category)
    if items is None:
        raise HTTPException(status_code=404, detail=f"Unknown category: {category}")

    for i, item in enumerate(items):
        if item.get("symbol") == symbol:
            items.pop(i)
            save_instruments(instruments)
            reload_settings()
            return {"success": True, "deleted": symbol}

    raise HTTPException(status_code=404, detail=f"Instrument not found: {symbol}")
