"""Action Items — separate Telegram message with levels, risk flags, and economic context."""

from src.digest.builder import DigestBuilder
from src.digest.formatter import bold, code, esc, italic, section_header, _safe_float
from src.analysis.technicals import get_rsi_label, get_trend_emoji
from src.analysis.events import get_event_context, get_next_fomc_date
from src.utils.logging_config import get_logger

logger = get_logger("action_items")

# Priority instruments for Section 1 (Key Levels)
PRIORITY_INSTRUMENTS = [
    "ES=F", "NQ=F", "YM=F",       # SPX, NDX, DJI futures
    "EURUSD", "GBPUSD", "USDJPY", # Forex majors
    "GC=F", "CL=F", "BTC",        # Gold, Crude, BTC
]

# Friendly display names
_DISPLAY_NAMES = {
    "ES=F": "SPX", "NQ=F": "NDX", "YM=F": "DJI",
    "EURUSD": "EUR/USD", "GBPUSD": "GBP/USD", "USDJPY": "USD/JPY",
    "GC=F": "Gold", "CL=F": "Crude", "BTC": "BTC",
}


def build_action_items(builder: DigestBuilder, digest_type: str, mode: str, digest_data: dict) -> str | None:
    """Build the action items message from accumulated digest data.

    Args:
        builder: DigestBuilder instance (for fetching yield/FRED if missing).
        digest_type: "morning", "afternoon", or "weekly".
        mode: "facts" or "full".
        digest_data: Accumulated data dict from the main digest build.

    Returns:
        Formatted Telegram HTML string, or None if insufficient data.
    """
    parts = []

    # Header
    type_label = digest_type.upper()
    parts.append(
        f"🎯 {bold(f'{type_label} ACTION ITEMS')}\n"
    )

    # Optional LLM summary (full mode only)
    if mode == "full":
        try:
            summary = _generate_llm_summary(builder, digest_data)
            if summary:
                parts.append(f"<blockquote>{esc(summary)}</blockquote>")
        except Exception as e:
            logger.warning(f"Action items LLM summary failed: {e}")

    # Section 1: Key Levels & Technicals
    levels_section = _build_key_levels(digest_data)
    if levels_section:
        parts.append(levels_section)

    # Section 2: Risk Flags & Alerts
    flags_section = _build_risk_flags(digest_data)
    parts.append(flags_section)

    # Section 3: Economic Context
    econ_section = _build_economic_context(builder, digest_data, digest_type)
    if econ_section:
        parts.append(econ_section)

    # Footer
    parts.append(f"\n{esc('─' * 30)}\n{italic('Use levels as reference, not trading advice.')}")

    result = "\n".join(parts)
    if len(result) < 100:
        return None

    return result


def _build_key_levels(digest_data: dict) -> str | None:
    """Section 1: Key Levels & Technicals for top priority instruments."""
    technicals = digest_data.get("technicals", {})
    if not technicals:
        return None

    lines = [section_header("📐 KEY LEVELS & TECHNICALS")]

    # Collect instruments in priority order
    shown = set()
    entries = []

    for sym in PRIORITY_INSTRUMENTS:
        ta = technicals.get(sym)
        if ta and not ta.get("error"):
            entries.append((sym, ta))
            shown.add(sym)

    # Backfill with RSI-extreme instruments if we have gaps
    if len(entries) < 8:
        for sym, ta in technicals.items():
            if sym in shown or ta.get("error"):
                continue
            rsi = ta.get("rsi")
            if rsi is not None and (rsi >= 70 or rsi <= 30):
                entries.append((sym, ta))
                shown.add(sym)
            if len(entries) >= 8:
                break

    if not entries:
        return None

    for sym, ta in entries[:8]:
        display = _DISPLAY_NAMES.get(sym, ta.get("name", sym))
        rsi = ta.get("rsi")
        trend = ta.get("trend", "neutral")
        trend_emoji = get_trend_emoji(trend)
        rsi_label = get_rsi_label(rsi) if rsi else ""

        # RSI part
        if rsi is not None:
            rsi_tag = f" ({esc(rsi_label)})" if rsi_label and rsi_label != "Neutral" else ""
            rsi_str = f"RSI {code(f'{rsi:.0f}')}{rsi_tag}"
        else:
            rsi_str = "RSI N/A"

        # Levels: prefer pivots R1/S1, fallback to support/resistance
        pivots = ta.get("pivots", {})
        sr = ta.get("support_resistance", {})
        r1 = pivots.get("r1")
        s1 = pivots.get("s1")
        if r1 is None and sr.get("resistance"):
            r1 = sr["resistance"][0]
        if s1 is None and sr.get("support"):
            s1 = sr["support"][0]

        level_str = ""
        if r1 is not None and s1 is not None:
            level_str = f" | R1: {code(f'{r1:,.2f}')}  S1: {code(f'{s1:,.2f}')}"
        elif r1 is not None:
            level_str = f" | R1: {code(f'{r1:,.2f}')}"
        elif s1 is not None:
            level_str = f" | S1: {code(f'{s1:,.2f}')}"

        lines.append(
            f"  {esc(display)}: {rsi_str} | {trend_emoji} {esc(trend)}{level_str}"
        )

    return "\n".join(lines)


def _build_risk_flags(digest_data: dict) -> str:
    """Section 2: Risk Flags & Alerts — conditional, severity-sorted."""
    flags = []  # list of (severity, text)

    technicals = digest_data.get("technicals", {})
    all_prices = {}
    # Gather prices from various digest data keys
    for key in ("futures", "forex", "commodities", "crypto", "indices_close"):
        d = digest_data.get(key, {})
        if isinstance(d, dict):
            all_prices.update(d)

    # 1. RSI extremes (>= 75 or <= 25)
    for sym, ta in technicals.items():
        if ta.get("error"):
            continue
        rsi = ta.get("rsi")
        if rsi is None:
            continue
        name = _DISPLAY_NAMES.get(sym, ta.get("name", sym))
        if rsi >= 75:
            sev = 90 + rsi  # higher RSI = more severe
            flags.append((sev, f"  ⚠️ {esc(name)} RSI {code(f'{rsi:.0f}')} — OVERBOUGHT extreme"))
        elif rsi <= 25:
            sev = 90 + (100 - rsi)
            flags.append((sev, f"  ⚠️ {esc(name)} RSI {code(f'{rsi:.0f}')} — OVERSOLD extreme"))

    # 2. VIX spike
    vix_data = all_prices.get("VIX") or digest_data.get("futures", {}).get("VIX", {})
    if not vix_data:
        # try fetching from all_prices in sentiment
        sentiment = digest_data.get("sentiment", {})
        vix_comp = sentiment.get("components", {}).get("vix", {})
        vix_val = vix_comp.get("raw_value")
        if vix_val and vix_val > 25:
            label = "PANIC" if vix_val > 30 else "elevated fear"
            sev = 200 if vix_val > 30 else 150
            flags.append((sev, f"  ⚠️ VIX at {code(f'{vix_val:.1f}')} — {esc(label)}"))
    else:
        vix_price = _safe_float(vix_data.get("price"))
        if vix_price > 25:
            label = "PANIC" if vix_price > 30 else "elevated fear"
            sev = 200 if vix_price > 30 else 150
            flags.append((sev, f"  ⚠️ VIX at {code(f'{vix_price:.1f}')} — {esc(label)}"))

    # 3. Yield curve inversion / near-flat
    econ_data = digest_data.get("economic", {})
    spread_data = econ_data.get("spread") if isinstance(econ_data, dict) else None
    if spread_data:
        spread_val = _safe_float(spread_data.get("spread"))
        if spread_val < 0:
            flags.append((180, f"  ⚠️ Yield curve INVERTED ({code(f'{spread_val:.2f}%')}) — recession signal"))
        elif 0 < spread_val < 0.20:
            flags.append((120, f"  ⚠️ Yield curve near-flat ({code(f'{spread_val:.2f}%')})"))

    # 4. Big moves (abs change > 1.5%)
    for sym, data in all_prices.items():
        if not isinstance(data, dict):
            continue
        chg = _safe_float(data.get("change_pct"))
        if abs(chg) > 1.5:
            name = _DISPLAY_NAMES.get(sym, data.get("name", sym))
            direction = "surged" if chg > 0 else "dropped"
            label = "breakout" if chg > 0 else "breakdown"
            sev = 100 + abs(chg) * 10
            flags.append((sev, f"  ⚠️ {esc(name)} {esc(direction)} {code(f'{chg:+.1f}%')} — {esc(label)}"))

    # 5. DXY surge (abs change > 0.5%)
    dxy = digest_data.get("forex", {}).get("DXY", {})
    if isinstance(dxy, dict):
        dxy_chg = _safe_float(dxy.get("change_pct"))
        if abs(dxy_chg) > 0.5:
            direction = "surged" if dxy_chg > 0 else "dropped"
            signal = "risk-off signal" if dxy_chg > 0 else "risk-on signal"
            flags.append((140, f"  ⚠️ DXY {esc(direction)} {code(f'{dxy_chg:+.1f}%')} — {esc(signal)}"))

    # 6. Sentiment extreme
    sentiment = digest_data.get("sentiment", {})
    if isinstance(sentiment, dict):
        score = sentiment.get("composite_score")
        if score is not None:
            if score >= 80:
                flags.append((160, f"  ⚠️ Sentiment {code(f'{score:.0f}/100')} (Extreme Greed) — contrarian alert"))
            elif score <= 20:
                flags.append((160, f"  ⚠️ Sentiment {code(f'{score:.0f}/100')} (Extreme Fear) — contrarian alert"))

    # Sort by severity descending, cap at 8
    flags.sort(key=lambda x: x[0], reverse=True)
    flag_lines = [f[1] for f in flags[:8]]

    result_lines = [section_header("⚠️ RISK FLAGS & ALERTS")]
    if flag_lines:
        result_lines.extend(flag_lines)
    else:
        result_lines.append(f"  {esc('No risk flags triggered.')}")

    return "\n".join(result_lines)


def _build_economic_context(builder: DigestBuilder, digest_data: dict, digest_type: str) -> str | None:
    """Section 3: Economic Context — events, yields, FRED macro pulse."""
    lines = [section_header("📊 ECONOMIC CONTEXT")]
    has_content = False

    # 3a. Upcoming events with "why it matters"
    events_data = digest_data.get("events", {})
    econ_events = events_data.get("economic_events", []) if isinstance(events_data, dict) else []
    upcoming = [e for e in econ_events if e.get("actual") is None]

    if upcoming:
        lines.append(f"  {bold('Upcoming Events')}")
        for event in upcoming[:5]:
            event_name = event.get("event", "Unknown")
            est = event.get("estimate")
            prev = event.get("prev")
            time_str = event.get("time", "")
            date_str = event.get("date", "")

            # Day abbreviation
            day_abbr = ""
            try:
                from datetime import datetime as _dt
                d = _dt.strptime(date_str, "%Y-%m-%d")
                day_abbr = d.strftime("%a")
            except (ValueError, TypeError):
                pass

            time_part = f" {esc(time_str)}" if time_str else ""
            line = f"  ⏳ {esc(event_name)} ({esc(day_abbr)}{time_part})"
            parts = []
            if est is not None:
                parts.append(f"Est: {code(str(est))}")
            if prev is not None:
                parts.append(f"Prev: {code(str(prev))}")
            if parts:
                line += f"  {' | '.join(parts)}"

            context = get_event_context(event_name)
            if context:
                line += f"\n    → {italic(esc(context))}"

            lines.append(line)
        has_content = True

    # 3b. Yield & rates snapshot
    econ = digest_data.get("economic", {})
    spread_data = econ.get("spread") if isinstance(econ, dict) else None
    econ_series = econ.get("econ", {}) if isinstance(econ, dict) else {}

    # Try to fetch yield data if not in digest_data
    if not spread_data:
        try:
            spread_data = builder.fetch_yield_spread()
        except Exception:
            pass
    if not econ_series:
        try:
            econ_series = builder.fetch_economic_data()
        except Exception:
            pass

    # Extract 10Y, 2Y yields from econ_series
    ten_y = econ_series.get("GS10", {})
    two_y = econ_series.get("GS2", {})
    fed_funds = econ_series.get("FEDFUNDS", {})

    yield_parts = []
    if ten_y.get("value"):
        ten_y_val = ten_y["value"]
        yield_parts.append(f"10Y: {code(f'{ten_y_val:.2f}%')}")
    if two_y.get("value"):
        two_y_val = two_y["value"]
        yield_parts.append(f"2Y: {code(f'{two_y_val:.2f}%')}")
    if spread_data:
        spread_val = _safe_float(spread_data.get("spread"))
        inv_tag = " ⚠️ INVERTED" if spread_data.get("inverted") else ""
        yield_parts.append(f"Spread: {code(f'{spread_val:.2f}%')}{inv_tag}")

    if yield_parts:
        lines.append(f"\n  {bold('Yields & Rates')}")
        lines.append(f"  {' | '.join(yield_parts)}")
        has_content = True

    if fed_funds.get("value"):
        ff_val = fed_funds["value"]
        ff_line = f"  Fed Funds: {code(f'{ff_val:.2f}%')}"
        fomc = get_next_fomc_date()
        if fomc:
            fomc_date, days = fomc
            ff_line += f" | Next FOMC: {esc(fomc_date.strftime('%b %d'))} ({days} days)"
        lines.append(ff_line)
        has_content = True

    # 3c. FRED macro pulse
    macro_keys = {
        "CPIAUCSL": "CPI",
        "UNRATE": "Unemployment",
        "A191RL1Q225SBEA": "GDP",
    }
    macro_lines = []
    for series_id, label in macro_keys.items():
        data = econ_series.get(series_id, {})
        if not data.get("value"):
            continue
        val = data["value"]
        prev = data.get("prev_value")
        if prev is not None:
            if val > prev:
                direction = "↑ rising"
            elif val < prev:
                direction = "↓ cooling"
            else:
                direction = "→ unchanged"
            macro_lines.append(f"  {esc(label)}: {code(f'{val:.2f}%')} (prev {code(f'{prev:.2f}%')}) {esc(direction)}")
        else:
            macro_lines.append(f"  {esc(label)}: {code(f'{val:.2f}%')}")

    if macro_lines:
        lines.append(f"\n  {bold('Macro Pulse')}")
        lines.extend(macro_lines)
        has_content = True

    if not has_content:
        return None

    return "\n".join(lines)


def _generate_llm_summary(builder: DigestBuilder, digest_data: dict) -> str | None:
    """Generate 2-3 sentence executive summary using LLM (full mode only)."""
    try:
        from src.analysis.llm_analyzer import MarketAnalyzer
        provider = builder.get_llm_provider()
        if not provider:
            return None
        analyzer = MarketAnalyzer(provider=provider)
        return analyzer.analyze_action_items_summary(digest_data)
    except Exception as e:
        logger.warning(f"LLM action items summary failed: {e}")
        return None
