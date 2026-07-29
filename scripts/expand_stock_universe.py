"""Expand the Compass stock universe with ~200 large/mid-cap companies.

Writes a `compass_stocks` group in instruments.yaml — deliberately separate
from `us_stocks` so digests and day-trade scoring never fetch these.
Idempotent; re-running refreshes names/sectors in place.
Run: .venv/bin/python scripts/expand_stock_universe.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import _load_instruments, save_instruments  # noqa: E402

# sector -> [(symbol, name)]  (~200 additions; excludes symbols already in us_stocks)
UNIVERSE: dict[str, list[tuple[str, str]]] = {
    "Technology": [
        ("TSM", "Taiwan Semiconductor"), ("ASML", "ASML Holding"), ("TXN", "Texas Instruments"),
        ("NOW", "ServiceNow"), ("INTU", "Intuit"), ("IBM", "IBM"), ("AMAT", "Applied Materials"),
        ("LRCX", "Lam Research"), ("KLAC", "KLA Corp"), ("SNPS", "Synopsys"), ("CDNS", "Cadence Design"),
        ("ANET", "Arista Networks"), ("PANW", "Palo Alto Networks"), ("CRWD", "CrowdStrike"),
        ("FTNT", "Fortinet"), ("ZS", "Zscaler"), ("DDOG", "Datadog"), ("SNOW", "Snowflake"),
        ("NET", "Cloudflare"), ("MDB", "MongoDB"), ("TEAM", "Atlassian"), ("WDAY", "Workday"),
        ("ADSK", "Autodesk"), ("SHOP", "Shopify"), ("UBER", "Uber"), ("ABNB", "Airbnb"),
        ("DASH", "DoorDash"), ("SPOT", "Spotify"), ("SMCI", "Super Micro Computer"),
        ("DELL", "Dell Technologies"), ("HPQ", "HP Inc"), ("CSCO", "Cisco"), ("ACN", "Accenture"),
        ("ADI", "Analog Devices"), ("MRVL", "Marvell Technology"), ("NXPI", "NXP Semiconductors"),
        ("MCHP", "Microchip Technology"), ("ON", "ON Semiconductor"), ("ARM", "Arm Holdings"),
    ],
    "Communication Services": [
        ("TMUS", "T-Mobile"), ("VZ", "Verizon"), ("T", "AT&T"), ("CMCSA", "Comcast"),
        ("CHTR", "Charter Communications"), ("EA", "Electronic Arts"), ("TTWO", "Take-Two Interactive"),
        ("RBLX", "Roblox"), ("PINS", "Pinterest"), ("WBD", "Warner Bros Discovery"),
        ("PARA", "Paramount"), ("LYV", "Live Nation"), ("OMC", "Omnicom"),
    ],
    "Financial Services": [
        ("BRK-B", "Berkshire Hathaway"), ("C", "Citigroup"), ("SCHW", "Charles Schwab"),
        ("BLK", "BlackRock"), ("AXP", "American Express"), ("USB", "US Bancorp"),
        ("PNC", "PNC Financial"), ("TFC", "Truist"), ("BK", "BNY Mellon"), ("STT", "State Street"),
        ("SPGI", "S&P Global"), ("MCO", "Moody's"), ("ICE", "Intercontinental Exchange"),
        ("CME", "CME Group"), ("NDAQ", "Nasdaq Inc"), ("MSCI", "MSCI"), ("AON", "Aon"),
        ("MMC", "Marsh & McLennan"), ("AJG", "Arthur J. Gallagher"), ("PGR", "Progressive"),
        ("ALL", "Allstate"), ("TRV", "Travelers"), ("CB", "Chubb"), ("AIG", "AIG"),
        ("MET", "MetLife"), ("PRU", "Prudential"), ("AFL", "Aflac"), ("DFS", "Discover"),
        ("SYF", "Synchrony"), ("FI", "Fiserv"), ("FIS", "Fidelity National Info"),
        ("GPN", "Global Payments"), ("HOOD", "Robinhood"), ("KKR", "KKR"), ("BX", "Blackstone"),
        ("APO", "Apollo Global"), ("ARES", "Ares Management"),
    ],
    "Healthcare": [
        ("ABBV", "AbbVie"), ("TMO", "Thermo Fisher"), ("ABT", "Abbott Labs"), ("DHR", "Danaher"),
        ("BMY", "Bristol Myers Squibb"), ("AMGN", "Amgen"), ("GILD", "Gilead Sciences"),
        ("VRTX", "Vertex Pharmaceuticals"), ("REGN", "Regeneron"), ("MRNA", "Moderna"),
        ("BIIB", "Biogen"), ("ZTS", "Zoetis"), ("ISRG", "Intuitive Surgical"), ("SYK", "Stryker"),
        ("BSX", "Boston Scientific"), ("MDT", "Medtronic"), ("EW", "Edwards Lifesciences"),
        ("BDX", "Becton Dickinson"), ("CI", "Cigna"), ("CVS", "CVS Health"), ("ELV", "Elevance"),
        ("HUM", "Humana"), ("HCA", "HCA Healthcare"), ("MCK", "McKesson"), ("COR", "Cencora"),
        ("NVO", "Novo Nordisk"), ("AZN", "AstraZeneca"),
    ],
    "Consumer Cyclical": [
        ("TM", "Toyota Motor"), ("F", "Ford"), ("GM", "General Motors"), ("LCID", "Lucid Motors"),
        ("MAR", "Marriott"), ("HLT", "Hilton"), ("BKNG", "Booking Holdings"), ("RCL", "Royal Caribbean"),
        ("CCL", "Carnival"), ("LVS", "Las Vegas Sands"), ("MGM", "MGM Resorts"),
        ("CMG", "Chipotle"), ("YUM", "Yum Brands"), ("DPZ", "Domino's Pizza"), ("QSR", "Restaurant Brands"),
        ("LULU", "Lululemon"), ("TJX", "TJX Companies"), ("ROST", "Ross Stores"),
        ("BURL", "Burlington"), ("DG", "Dollar General"), ("DLTR", "Dollar Tree"),
        ("LOW", "Lowe's"), ("TGT", "Target"), ("BBY", "Best Buy"), ("EBAY", "eBay"),
        ("ETSY", "Etsy"), ("W", "Wayfair"), ("CHWY", "Chewy"), ("ORLY", "O'Reilly Automotive"),
        ("AZO", "AutoZone"), ("GPC", "Genuine Parts"),
    ],
    "Consumer Defensive": [
        ("PG", "Procter & Gamble"), ("KO", "Coca-Cola"), ("PEP", "PepsiCo"), ("PM", "Philip Morris"),
        ("MO", "Altria"), ("MDLZ", "Mondelez"), ("KHC", "Kraft Heinz"), ("GIS", "General Mills"),
        ("K", "Kellanova"), ("HSY", "Hershey"), ("STZ", "Constellation Brands"), ("KMB", "Kimberly-Clark"),
        ("CL", "Colgate-Palmolive"), ("CHD", "Church & Dwight"), ("EL", "Estee Lauder"),
        ("KR", "Kroger"), ("SYY", "Sysco"), ("ADM", "Archer-Daniels-Midland"),
    ],
    "Energy": [
        ("SLB", "Schlumberger"), ("EOG", "EOG Resources"), ("PXD", "Pioneer Natural"),
        ("MPC", "Marathon Petroleum"), ("PSX", "Phillips 66"), ("VLO", "Valero"),
        ("OXY", "Occidental"), ("HES", "Hess"), ("DVN", "Devon Energy"), ("HAL", "Halliburton"),
        ("KMI", "Kinder Morgan"), ("WMB", "Williams Companies"), ("OKE", "ONEOK"),
        ("LNG", "Cheniere Energy"), ("FANG", "Diamondback Energy"),
    ],
    "Industrials": [
        ("HON", "Honeywell"), ("GE", "GE Aerospace"), ("RTX", "RTX Corp"), ("LMT", "Lockheed Martin"),
        ("NOC", "Northrop Grumman"), ("GD", "General Dynamics"), ("MMM", "3M"),
        ("ETN", "Eaton"), ("EMR", "Emerson Electric"), ("ITW", "Illinois Tool Works"),
        ("PH", "Parker Hannifin"), ("CMI", "Cummins"), ("PCAR", "PACCAR"), ("CSX", "CSX"),
        ("UNP", "Union Pacific"), ("NSC", "Norfolk Southern"), ("FDX", "FedEx"),
        ("DAL", "Delta Air Lines"), ("UAL", "United Airlines"), ("LUV", "Southwest Airlines"),
        ("WM", "Waste Management"), ("RSG", "Republic Services"), ("URI", "United Rentals"),
        ("FAST", "Fastenal"), ("GWW", "W.W. Grainger"), ("CARR", "Carrier Global"),
        ("OTIS", "Otis Worldwide"), ("JCI", "Johnson Controls"),
    ],
    "Utilities": [
        ("NEE", "NextEra Energy"), ("DUK", "Duke Energy"), ("SO", "Southern Company"),
        ("D", "Dominion Energy"), ("AEP", "American Electric Power"), ("EXC", "Exelon"),
        ("SRE", "Sempra"), ("XEL", "Xcel Energy"), ("ED", "Consolidated Edison"),
        ("PCG", "PG&E"), ("CEG", "Constellation Energy"), ("VST", "Vistra"),
    ],
    "Basic Materials": [
        ("LIN", "Linde"), ("APD", "Air Products"), ("SHW", "Sherwin-Williams"),
        ("ECL", "Ecolab"), ("FCX", "Freeport-McMoRan"), ("NEM", "Newmont"),
        ("NUE", "Nucor"), ("STLD", "Steel Dynamics"), ("DOW", "Dow"), ("DD", "DuPont"),
        ("ALB", "Albemarle"), ("MOS", "Mosaic"),
    ],
    "Real Estate": [
        ("PLD", "Prologis"), ("AMT", "American Tower"), ("EQIX", "Equinix"),
        ("CCI", "Crown Castle"), ("SPG", "Simon Property"), ("O", "Realty Income"),
        ("PSA", "Public Storage"), ("WELL", "Welltower"), ("DLR", "Digital Realty"),
        ("AVB", "AvalonBay"), ("EQR", "Equity Residential"), ("VICI", "VICI Properties"),
    ],
}


def main() -> None:
    instruments = _load_instruments()
    existing_dt = {s["symbol"] for s in instruments.get("us_stocks", [])}
    existing_compass = {s["symbol"]: s for s in instruments.get("compass_stocks", [])}

    rows = []
    for sector, names in UNIVERSE.items():
        for symbol, name in names:
            if symbol in existing_dt:
                continue  # already tracked in the day-trade universe
            entry = existing_compass.get(symbol, {"enabled": True})
            entry.update({
                "symbol": symbol,
                "yfinance": symbol,
                "name": name,
                "sector": sector,
                "asset_class": "us_stock",
            })
            entry.setdefault("enabled", True)
            rows.append(entry)

    # Foreign large caps traded as ADRs shouldn't count as US exposure
    for intl in ("TSM", "ASML", "TM", "NVO", "AZN", "SPOT", "SHOP", "ARM"):
        for row in rows:
            if row["symbol"] == intl:
                row["asset_class"] = "intl_stock"

    rows.sort(key=lambda r: r["symbol"])
    instruments["compass_stocks"] = rows
    save_instruments(instruments)
    print(f"compass_stocks: {len(rows)} companies across {len(UNIVERSE)} sectors")


if __name__ == "__main__":
    main()
