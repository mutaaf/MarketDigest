"""Telegram HTML formatting and message splitting (4096 char limit)."""

import html
import math
from typing import Any

from src.analysis.performance import change_indicator


def _safe_float(value, default: float = 0.0) -> float:
    """Convert value to float, returning default for None/NaN/Inf."""
    if value is None:
        return default
    try:
        f = float(value)
        return default if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return default


MAX_MESSAGE_LENGTH = 4096


def bold(text: str) -> str:
    return f"<b>{esc(text)}</b>"


def italic(text: str) -> str:
    return f"<i>{esc(text)}</i>"


def code(text: str) -> str:
    return f"<code>{esc(text)}</code>"


def esc(text: str) -> str:
    return html.escape(str(text), quote=False)


def section_header(title: str) -> str:
    return f"\n\n<b>{'━' * 20}</b>\n<b>{esc(title)}</b>\n"


def price_line(name: str, price: float, change_pct: float, decimals: int = 2) -> str:
    """Format a single price line with color-coded change."""
    price = _safe_float(price)
    change_pct = _safe_float(change_pct)
    indicator = change_indicator(change_pct)
    return f"  {esc(name)}: {code(f'{price:,.{decimals}f}')}  {indicator}"


def forex_line(name: str, price: float, change_pct: float, pivots: dict | None = None) -> str:
    """Format forex pair with optional pivot levels."""
    price = _safe_float(price)
    change_pct = _safe_float(change_pct)
    indicator = change_indicator(change_pct)
    line = f"  {esc(name)}: {code(f'{price:.5f}')}  {indicator}"
    if pivots:
        r1 = _safe_float(pivots.get('r1'))
        s1 = _safe_float(pivots.get('s1'))
        line += f"\n    R1: {code(f'{r1:.5f}')} | S1: {code(f'{s1:.5f}')}"
    return line


def commodity_line(name: str, price: float, change_pct: float) -> str:
    return price_line(name, price, change_pct, decimals=2)


def index_line(name: str, price: float, change_pct: float) -> str:
    return price_line(name, price, change_pct, decimals=2)


def economic_event_line(event: dict) -> str:
    """Format a single economic calendar event."""
    impact_icon = "🔴" if event.get("impact") == "high" else "🟡"
    line = f"  {impact_icon} {esc(event.get('event', 'Unknown'))}"

    actual = event.get("actual")
    estimate = event.get("estimate")
    prev = event.get("prev")

    parts = []
    if actual is not None:
        parts.append(f"Actual: {code(str(actual))}")
    if estimate is not None:
        parts.append(f"Est: {code(str(estimate))}")
    if prev is not None:
        parts.append(f"Prev: {code(str(prev))}")

    if parts:
        line += f"\n    {' | '.join(parts)}"
    return line


def comprehensive_event_line(event: dict, show_context: bool = True) -> str:
    """Format an economic event with beat/miss indicator and optional context line."""
    from src.analysis.events import get_event_context

    actual = event.get("actual")
    estimate = event.get("estimate")
    prev = event.get("prev")
    event_name = event.get("event", "Unknown")
    event_date = event.get("date", "")

    # Day-of-week prefix
    try:
        from datetime import datetime as _dt
        d = _dt.strptime(event_date, "%Y-%m-%d")
        day_abbr = d.strftime("%a")
    except (ValueError, TypeError):
        day_abbr = ""

    # Status icon and beat/miss
    if actual is not None:
        # Released — check beat/miss
        beat_miss = ""
        if estimate is not None:
            try:
                a, e = float(actual), float(estimate)
                if a > e:
                    beat_miss = " Beat"
                elif a < e:
                    beat_miss = " Miss"
                else:
                    beat_miss = " In-line"
            except (TypeError, ValueError):
                pass
        icon = "+" if "Beat" in beat_miss else ("-" if "Miss" in beat_miss else "=")
        line = f"  {icon} {day_abbr} — {esc(event_name)}: {code(str(actual))}"
        if estimate is not None:
            line += f" (Est: {code(str(estimate))})"
        if beat_miss:
            line += f" {esc(beat_miss)}"
    else:
        # Upcoming
        time_str = event.get("time", "")
        time_part = f" {esc(time_str)}" if time_str else ""
        line = f"  ... {day_abbr}{time_part} — {esc(event_name)}"
        if estimate is not None:
            line += f"  Est: {code(str(estimate))}"
        if prev is not None:
            line += f"  Prev: {code(str(prev))}"

    # Context line
    if show_context:
        ctx = get_event_context(event_name)
        if ctx:
            line += f"\n    > {italic(esc(ctx))}"

    return line


def earnings_line(earning: dict) -> str:
    """Format a single earnings entry with beat/miss indicator."""
    symbol = earning.get("symbol", "?")
    eps_actual = earning.get("eps_actual")
    eps_estimate = earning.get("eps_estimate")
    earning_date = earning.get("date", "")
    hour = earning.get("hour", "")

    # Day-of-week
    try:
        from datetime import datetime as _dt
        d = _dt.strptime(earning_date, "%Y-%m-%d")
        day_abbr = d.strftime("%a")
    except (ValueError, TypeError):
        day_abbr = ""

    # Hour label
    hour_label = ""
    if hour == "bmo":
        hour_label = " BMO"
    elif hour == "amc":
        hour_label = " AMC"

    if eps_actual is not None:
        # Released
        beat_miss = ""
        if eps_estimate is not None:
            try:
                a, e = float(eps_actual), float(eps_estimate)
                if a > e:
                    beat_miss = " Beat"
                elif a < e:
                    beat_miss = " Miss"
                else:
                    beat_miss = " In-line"
            except (TypeError, ValueError):
                pass
        icon = "+" if "Beat" in beat_miss else ("-" if "Miss" in beat_miss else "=")
        line = f"  {icon} {day_abbr} — {bold(esc(symbol))}: EPS {code(str(eps_actual))}"
        if eps_estimate is not None:
            line += f" vs {code(str(eps_estimate))} est"
        if beat_miss:
            line += f" {esc(beat_miss)}"
    else:
        # Upcoming
        line = f"  ... {day_abbr}{esc(hour_label)} — {bold(esc(symbol))}"
        if eps_estimate is not None:
            line += f"  Est EPS: {code(str(eps_estimate))}"

    return line


def forward_calendar_block(items: list[dict]) -> str:
    """Format forward-looking calendar countdown items."""
    lines = []
    for item in items:
        event = item.get("event", "")
        formatted = item.get("formatted", "")
        lines.append(f"  {esc(event)}: {esc(formatted)}")
    return "\n".join(lines)


def sentiment_block(sentiment_data: dict) -> str:
    """Format sentiment overview block."""
    score = _safe_float(sentiment_data.get("composite_score"), default=50)
    classification = sentiment_data.get("classification", "N/A")

    # Build score bar
    filled = int(score) // 5
    bar = "█" * filled + "░" * (20 - filled)

    lines = [
        f"  Sentiment: {code(f'{score}/100')} — {bold(classification)}",
        f"  {code(f'[{bar}]')}",
    ]

    components = sentiment_data.get("components", {})
    for name, comp in components.items():
        if comp.get("weight", 0) > 0:
            lines.append(f"    {esc(name.upper())}: {comp.get('score', 'N/A')} — {esc(comp.get('label', ''))}")

    return "\n".join(lines)


def session_block(session_name: str, data: dict[str, dict]) -> str:
    """Format session performance block."""
    if not data:
        return f"  {esc(session_name.title())}: No data available"

    lines = [f"  {bold(session_name.title() + ' Session')}"]
    for ticker, perf in data.items():
        name = perf.get("name", ticker)
        indicator = change_indicator(_safe_float(perf.get("change_pct")))
        close_val = _safe_float(perf.get('close'))
        high_val = _safe_float(perf.get('high'))
        low_val = _safe_float(perf.get('low'))
        lines.append(
            f"    {esc(name)}: {code(f'{close_val:.4f}')} {indicator} "
            f"(H: {code(f'{high_val:.4f}')} L: {code(f'{low_val:.4f}')})"
        )
    return "\n".join(lines)


def movers_block(movers: dict[str, list[dict]]) -> str:
    """Format top movers block."""
    lines = []
    if movers.get("gainers"):
        lines.append(f"  {bold('Top Gainers')}")
        for g in movers["gainers"][:5]:
            lines.append(f"    🟢 {esc(g.get('name', ''))} {change_indicator(g.get('change_pct', 0))}")

    if movers.get("losers"):
        lines.append(f"  {bold('Top Losers')}")
        for l in movers["losers"][:5]:
            lines.append(f"    🔴 {esc(l.get('name', ''))} {change_indicator(l.get('change_pct', 0))}")

    return "\n".join(lines)


def analysis_block(text: str) -> str:
    """Wrap LLM analysis text in blockquote, visually distinct from data."""
    return f"\n\n<blockquote>{esc(text)}</blockquote>"


def quick_take_block(text: str) -> str:
    """Format Quick Take text as individual bolded-prefix lines.

    Splits on newlines, bolds recognized prefixes (Bullish:, Bearish:, etc.),
    and returns formatted lines suitable for Telegram HTML.
    """
    prefixes = ("Bullish:", "Bearish:", "Event:", "Data:", "Earnings:")
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    formatted = []
    for line in lines:
        for prefix in prefixes:
            if line.startswith(prefix):
                rest = line[len(prefix):]
                line = f"<b>{esc(prefix)}</b>{esc(rest)}"
                break
        else:
            line = esc(line)
        formatted.append(f"  {line}")
    return "\n".join(formatted)


def unavailable(section: str) -> str:
    return f"  {italic(f'{esc(section)} data temporarily unavailable')}"


def split_message(text: str) -> list[str]:
    """Split message into chunks ≤4096 chars, breaking at section boundaries."""
    if len(text) <= MAX_MESSAGE_LENGTH:
        return [text]

    messages = []
    current = ""

    # Split on section headers (lines starting with ━)
    sections = text.split("\n<b>━")
    for i, section in enumerate(sections):
        if i > 0:
            section = "<b>━" + section

        if len(current) + len(section) + 1 > MAX_MESSAGE_LENGTH:
            if current:
                messages.append(current.strip())
            current = section
        else:
            current += "\n" + section if current else section

    if current.strip():
        messages.append(current.strip())

    # Final safety check — if any chunk is still too long, hard-split by lines
    final = []
    for msg in messages:
        if len(msg) <= MAX_MESSAGE_LENGTH:
            final.append(msg)
        else:
            chunk = ""
            for line in msg.split("\n"):
                if len(chunk) + len(line) + 1 > MAX_MESSAGE_LENGTH:
                    final.append(chunk.strip())
                    chunk = line
                else:
                    chunk += "\n" + line if chunk else line
            if chunk.strip():
                final.append(chunk.strip())

    return final
