"""Smart holdings extraction — read a brokerage screenshot or pasted text
into structured holdings for user review before import.

Nothing extracted here is saved directly; the API returns candidates and the
UI confirms with the user first.
"""

import json
import re

from src.utils.logging_config import get_logger

logger = get_logger("extract")

_SYSTEM_PROMPT = """You extract investment holdings from brokerage account screenshots or
copied text. Respond with ONLY a JSON array, no prose, no code fences:

[{"symbol": "AAPL", "shares": 10.5, "cost_basis": 150.25}]

Rules:
- symbol: the ticker. If only a company/fund name is shown, use its well-known
  ticker (e.g. "Vanguard S&P 500 ETF" -> "VOO", "Apple Inc" -> "AAPL"). If you
  cannot identify a ticker confidently, skip the row.
- shares: number of shares/units. Required — skip rows without a quantity.
- cost_basis: average price PAID per share if shown (cost basis / avg cost).
  If a total cost is clearly shown, divide by shares. When a price is ambiguous
  (could be per-share or total), prefer per-share if that's a plausible price
  for the security. If unknown, use 0. Never use the current market price.
- Skip cash rows, totals, headers, pending activity, and non-security rows.
- If nothing extractable, return []."""

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


def _parse_llm_json(text: str) -> list[dict]:
    """Tolerant JSON extraction — strips code fences and finds the array."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.MULTILINE).strip()
    if not cleaned.startswith("["):
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if not match:
            return []
        cleaned = match.group(0)
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _validate(rows: list[dict]) -> tuple[list[dict], list[str]]:
    holdings, warnings = [], []
    seen = set()
    for row in rows:
        try:
            symbol = str(row.get("symbol", "")).strip().upper()
            shares = float(row.get("shares", 0))
            cost = float(row.get("cost_basis") or 0)
            if not _TICKER_RE.match(symbol):
                warnings.append(f"Skipped '{symbol or '?'}' — doesn't look like a ticker.")
                continue
            if shares <= 0:
                warnings.append(f"Skipped {symbol} — no share count found.")
                continue
            if symbol in seen:
                continue
            seen.add(symbol)
            holdings.append({"symbol": symbol, "shares": round(shares, 6),
                             "cost_basis": round(max(cost, 0), 4), "account": ""})
        except (TypeError, ValueError):
            warnings.append("Skipped one row that couldn't be read.")
    return holdings, warnings


def extract_from_image(image_b64: str, media_type: str) -> dict:
    """Read holdings from a screenshot via the LLM vision chain."""
    from config.settings import get_settings
    from src.analysis.llm_providers import LLMProvider

    if not get_settings().has_llm_key():
        return {"holdings": [], "warnings": [], "source": "none",
                "error": "Reading screenshots needs an AI key (Anthropic, OpenAI, or "
                         "Gemini) — add one on the Settings page, or use CSV import."}

    result = LLMProvider().generate_with_image(
        _SYSTEM_PROMPT,
        "Extract the holdings from this brokerage screenshot.",
        image_b64, media_type,
    )
    if result is None:
        return {"holdings": [], "warnings": [], "source": "ai",
                "error": "Couldn't read the image right now. Try again in a minute, "
                         "or use CSV import."}

    holdings, warnings = _validate(_parse_llm_json(result.text))
    if not holdings:
        return {"holdings": [], "warnings": warnings, "source": "ai",
                "error": "No holdings found in that image. Make sure the screenshot "
                         "shows your positions with symbols and share counts."}
    return {"holdings": holdings, "warnings": warnings, "source": "ai"}


def extract_from_text(text: str) -> dict:
    """Read holdings from pasted text. Tries the fast CSV parser first;
    falls back to the LLM for messy copied tables."""
    from src.portfolio.store import parse_csv

    holdings, skipped = parse_csv(text)
    if holdings:
        return {"holdings": holdings, "warnings": skipped, "source": "csv"}

    from config.settings import get_settings
    if not get_settings().has_llm_key():
        return {"holdings": [], "warnings": skipped, "source": "csv",
                "error": skipped[0] if skipped else "Couldn't read that text."}

    from src.analysis.llm_providers import LLMProvider
    result = LLMProvider().generate(
        _SYSTEM_PROMPT,
        f"Extract the holdings from this text copied from a brokerage account:\n\n{text[:8000]}",
        max_tokens=1500,
    )
    if result is None:
        return {"holdings": [], "warnings": [], "source": "ai",
                "error": "Couldn't read that text right now. Try again in a minute."}

    holdings, warnings = _validate(_parse_llm_json(result.text))
    if not holdings:
        return {"holdings": [], "warnings": warnings, "source": "ai",
                "error": "No holdings found in that text. Copy the rows that show "
                         "each investment with its symbol and share count."}
    return {"holdings": holdings, "warnings": warnings, "source": "ai"}
