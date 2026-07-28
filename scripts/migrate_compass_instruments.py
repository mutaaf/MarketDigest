"""One-off migration: add sector/asset_class to us_stocks and add the Compass ETF universe.

Idempotent — safe to re-run; existing fields and ETFs are preserved/updated in place.
Run: .venv/bin/python scripts/migrate_compass_instruments.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import _load_instruments, save_instruments  # noqa: E402

STOCK_SECTORS = {
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
    "AMD": "Technology", "INTC": "Technology", "MU": "Technology",
    "AVGO": "Technology", "QCOM": "Technology", "CRM": "Technology",
    "ADBE": "Technology", "ORCL": "Technology", "SQ": "Technology",
    "PLTR": "Technology",
    "TSLA": "Consumer Cyclical", "AMZN": "Consumer Cyclical", "BABA": "Consumer Cyclical",
    "HD": "Consumer Cyclical", "NKE": "Consumer Cyclical", "MCD": "Consumer Cyclical",
    "SBUX": "Consumer Cyclical", "RIVN": "Consumer Cyclical",
    "META": "Communication Services", "GOOGL": "Communication Services",
    "NFLX": "Communication Services", "DIS": "Communication Services",
    "SNAP": "Communication Services",
    "JPM": "Financial Services", "BAC": "Financial Services", "GS": "Financial Services",
    "WFC": "Financial Services", "MS": "Financial Services", "V": "Financial Services",
    "MA": "Financial Services", "PYPL": "Financial Services", "COIN": "Financial Services",
    "SOFI": "Financial Services",
    "XOM": "Energy", "CVX": "Energy", "COP": "Energy",
    "UNH": "Healthcare", "JNJ": "Healthcare", "PFE": "Healthcare",
    "LLY": "Healthcare", "MRK": "Healthcare",
    "WMT": "Consumer Defensive", "COST": "Consumer Defensive",
    "BA": "Industrials", "CAT": "Industrials", "UPS": "Industrials", "DE": "Industrials",
}

# ADRs that shouldn't count as US exposure in diversification math
INTL_STOCKS = {"BABA"}

# (symbol, name, category, asset_class)
ETFS = [
    # US broad market
    ("VOO", "Vanguard S&P 500", "us_broad", "us_stock"),
    ("VTI", "Vanguard Total Stock Market", "us_broad", "us_stock"),
    ("SPY", "SPDR S&P 500", "us_broad", "us_stock"),
    ("IVV", "iShares Core S&P 500", "us_broad", "us_stock"),
    ("QQQ", "Invesco NASDAQ 100", "us_broad", "us_stock"),
    ("DIA", "SPDR Dow Jones", "us_broad", "us_stock"),
    ("RSP", "Invesco S&P 500 Equal Weight", "us_broad", "us_stock"),
    ("ITOT", "iShares Core Total US Market", "us_broad", "us_stock"),
    ("SCHB", "Schwab US Broad Market", "us_broad", "us_stock"),
    ("SCHX", "Schwab US Large-Cap", "us_broad", "us_stock"),
    ("VV", "Vanguard Large-Cap", "us_broad", "us_stock"),
    ("VO", "Vanguard Mid-Cap", "us_mid", "us_stock"),
    ("VB", "Vanguard Small-Cap", "us_small", "us_stock"),
    ("IWM", "iShares Russell 2000", "us_small", "us_stock"),
    ("VBK", "Vanguard Small-Cap Growth", "us_small", "us_stock"),
    ("VBR", "Vanguard Small-Cap Value", "us_small", "us_stock"),
    # US growth / value
    ("VUG", "Vanguard Growth", "us_large_growth", "us_stock"),
    ("IWF", "iShares Russell 1000 Growth", "us_large_growth", "us_stock"),
    ("SCHG", "Schwab US Large-Cap Growth", "us_large_growth", "us_stock"),
    ("MGK", "Vanguard Mega Cap Growth", "us_large_growth", "us_stock"),
    ("VTV", "Vanguard Value", "us_large_value", "us_stock"),
    ("IWD", "iShares Russell 1000 Value", "us_large_value", "us_stock"),
    ("SCHV", "Schwab US Large-Cap Value", "us_large_value", "us_stock"),
    # International
    ("VXUS", "Vanguard Total International", "intl_broad", "intl_stock"),
    ("IXUS", "iShares Core Total International", "intl_broad", "intl_stock"),
    ("VEA", "Vanguard Developed Markets", "intl_developed", "intl_stock"),
    ("IEFA", "iShares Core MSCI EAFE", "intl_developed", "intl_stock"),
    ("EFA", "iShares MSCI EAFE", "intl_developed", "intl_stock"),
    ("SCHF", "Schwab International Equity", "intl_developed", "intl_stock"),
    ("VGK", "Vanguard FTSE Europe", "intl_developed", "intl_stock"),
    ("VPL", "Vanguard FTSE Pacific", "intl_developed", "intl_stock"),
    ("EWJ", "iShares MSCI Japan", "intl_developed", "intl_stock"),
    ("VWO", "Vanguard Emerging Markets", "intl_emerging", "intl_stock"),
    ("IEMG", "iShares Core MSCI Emerging", "intl_emerging", "intl_stock"),
    ("EEM", "iShares MSCI Emerging Markets", "intl_emerging", "intl_stock"),
    ("INDA", "iShares MSCI India", "intl_emerging", "intl_stock"),
    ("MCHI", "iShares MSCI China", "intl_emerging", "intl_stock"),
    # Bonds
    ("BND", "Vanguard Total Bond Market", "bond_total", "bond"),
    ("AGG", "iShares Core US Aggregate Bond", "bond_total", "bond"),
    ("BSV", "Vanguard Short-Term Bond", "bond_total", "bond"),
    ("BIV", "Vanguard Intermediate-Term Bond", "bond_total", "bond"),
    ("VGSH", "Vanguard Short-Term Treasury", "bond_treasury", "bond"),
    ("VGIT", "Vanguard Intermediate Treasury", "bond_treasury", "bond"),
    ("VGLT", "Vanguard Long-Term Treasury", "bond_treasury", "bond"),
    ("TLT", "iShares 20+ Year Treasury", "bond_treasury", "bond"),
    ("IEF", "iShares 7-10 Year Treasury", "bond_treasury", "bond"),
    ("SHY", "iShares 1-3 Year Treasury", "bond_treasury", "bond"),
    ("GOVT", "iShares US Treasury Bond", "bond_treasury", "bond"),
    ("LQD", "iShares Investment Grade Corporate", "bond_corporate", "bond"),
    ("VCIT", "Vanguard Intermediate Corporate", "bond_corporate", "bond"),
    ("VCSH", "Vanguard Short-Term Corporate", "bond_corporate", "bond"),
    ("HYG", "iShares High Yield Corporate", "bond_corporate", "bond"),
    ("MUB", "iShares National Muni Bond", "bond_muni", "bond"),
    ("VTEB", "Vanguard Tax-Exempt Bond", "bond_muni", "bond"),
    ("TIP", "iShares TIPS Bond", "bond_tips", "bond"),
    ("SCHP", "Schwab US TIPS", "bond_tips", "bond"),
    ("VTIP", "Vanguard Short-Term TIPS", "bond_tips", "bond"),
    ("BNDX", "Vanguard Total International Bond", "bond_intl", "bond"),
    ("EMB", "iShares Emerging Markets Bond", "bond_intl", "bond"),
    # Dividend / income
    ("SCHD", "Schwab US Dividend Equity", "dividend", "us_stock"),
    ("VYM", "Vanguard High Dividend Yield", "dividend", "us_stock"),
    ("VIG", "Vanguard Dividend Appreciation", "dividend", "us_stock"),
    ("DGRO", "iShares Core Dividend Growth", "dividend", "us_stock"),
    ("HDV", "iShares Core High Dividend", "dividend", "us_stock"),
    ("DVY", "iShares Select Dividend", "dividend", "us_stock"),
    ("NOBL", "ProShares S&P 500 Dividend Aristocrats", "dividend", "us_stock"),
    ("SDY", "SPDR S&P Dividend", "dividend", "us_stock"),
    ("JEPI", "JPMorgan Equity Premium Income", "covered_call", "us_stock"),
    ("JEPQ", "JPMorgan Nasdaq Equity Premium", "covered_call", "us_stock"),
    # Sectors
    ("XLK", "Technology Select Sector SPDR", "sector_tech", "us_stock"),
    ("VGT", "Vanguard Information Technology", "sector_tech", "us_stock"),
    ("SMH", "VanEck Semiconductor", "sector_tech", "us_stock"),
    ("SOXX", "iShares Semiconductor", "sector_tech", "us_stock"),
    ("XLV", "Health Care Select Sector SPDR", "sector_health", "us_stock"),
    ("VHT", "Vanguard Health Care", "sector_health", "us_stock"),
    ("IBB", "iShares Biotechnology", "sector_health", "us_stock"),
    ("XLF", "Financial Select Sector SPDR", "sector_financial", "us_stock"),
    ("VFH", "Vanguard Financials", "sector_financial", "us_stock"),
    ("KRE", "SPDR S&P Regional Banking", "sector_financial", "us_stock"),
    ("XLE", "Energy Select Sector SPDR", "sector_energy", "us_stock"),
    ("VDE", "Vanguard Energy", "sector_energy", "us_stock"),
    ("XLI", "Industrial Select Sector SPDR", "sector_industrial", "us_stock"),
    ("ITA", "iShares US Aerospace & Defense", "sector_industrial", "us_stock"),
    ("XLY", "Consumer Discretionary SPDR", "sector_consumer_cyclical", "us_stock"),
    ("XLP", "Consumer Staples SPDR", "sector_consumer_defensive", "us_stock"),
    ("XLU", "Utilities Select Sector SPDR", "sector_utilities", "us_stock"),
    ("XLB", "Materials Select Sector SPDR", "sector_materials", "us_stock"),
    ("XLC", "Communication Services SPDR", "sector_communication", "us_stock"),
    # Real estate
    ("VNQ", "Vanguard Real Estate", "reit", "reit"),
    ("SCHH", "Schwab US REIT", "reit", "reit"),
    ("VNQI", "Vanguard Global ex-US Real Estate", "reit", "reit"),
    ("IYR", "iShares US Real Estate", "reit", "reit"),
    ("XLRE", "Real Estate Select Sector SPDR", "reit", "reit"),
    # Commodities / gold
    ("GLD", "SPDR Gold Shares", "gold", "commodity"),
    ("IAU", "iShares Gold Trust", "gold", "commodity"),
    ("SLV", "iShares Silver Trust", "gold", "commodity"),
    ("GDX", "VanEck Gold Miners", "gold", "commodity"),
    ("PDBC", "Invesco Optimum Yield Commodity", "commodity", "commodity"),
    ("DBC", "Invesco DB Commodity Index", "commodity", "commodity"),
    # Factor / defensive
    ("USMV", "iShares MSCI USA Min Volatility", "low_volatility", "us_stock"),
    ("SPLV", "Invesco S&P 500 Low Volatility", "low_volatility", "us_stock"),
    ("MTUM", "iShares MSCI USA Momentum", "factor", "us_stock"),
    ("QUAL", "iShares MSCI USA Quality", "factor", "us_stock"),
    ("COWZ", "Pacer US Cash Cows 100", "factor", "us_stock"),
    ("MOAT", "VanEck Morningstar Wide Moat", "factor", "us_stock"),
    # Thematic
    ("ARKK", "ARK Innovation", "thematic", "us_stock"),
    ("BOTZ", "Global X Robotics & AI", "thematic", "us_stock"),
    ("ICLN", "iShares Global Clean Energy", "thematic", "intl_stock"),
    ("TAN", "Invesco Solar", "thematic", "us_stock"),
    ("HACK", "Amplify Cybersecurity", "thematic", "us_stock"),
    ("ESGU", "iShares ESG Aware MSCI USA", "thematic", "us_stock"),
]


def main() -> None:
    instruments = _load_instruments()

    updated_stocks = 0
    for stock in instruments.get("us_stocks", []):
        sym = stock.get("symbol")
        if sym in STOCK_SECTORS and stock.get("sector") != STOCK_SECTORS[sym]:
            stock["sector"] = STOCK_SECTORS[sym]
            updated_stocks += 1
        asset_class = "intl_stock" if sym in INTL_STOCKS else "us_stock"
        if stock.get("asset_class") != asset_class:
            stock["asset_class"] = asset_class

    existing = {e["symbol"]: e for e in instruments.get("etfs", [])}
    etf_list = []
    for symbol, name, category, asset_class in ETFS:
        entry = existing.get(symbol, {"enabled": True})
        entry.update({
            "symbol": symbol,
            "yfinance": symbol,
            "name": name,
            "category": category,
            "asset_class": asset_class,
        })
        entry.setdefault("enabled", True)
        etf_list.append(entry)
    instruments["etfs"] = etf_list

    save_instruments(instruments)
    print(f"Updated sectors on {updated_stocks} stocks; wrote {len(etf_list)} ETFs.")


if __name__ == "__main__":
    main()
