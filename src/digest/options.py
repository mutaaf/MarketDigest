"""Options Flow digest — top 3 equity conviction picks with flow analysis."""

from config.settings import get_enabled_sections, get_settings
from src.analysis.options_flow import (
    analyze_options_flow,
    build_daily_breakdown,
    load_flow_history,
    save_flow_snapshot,
)
from src.digest.builder import DigestBuilder
from src.digest.formatter import (
    analysis_block,
    bold,
    code,
    esc,
    italic,
    section_header,
    unavailable,
)
from src.fetchers.options_fetcher import OptionsFetcher
from src.utils.logging_config import get_logger
from src.utils.timezone import format_date, format_time_ct, now_ct

logger = get_logger("options_digest")


def _format_premium(value: float) -> str:
    """Format dollar premium with K/M suffix."""
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:,.0f}"


def _conviction_emoji(label: str) -> str:
    """Map conviction label to emoji."""
    mapping = {
        "Extreme Bull": "\U0001f7e2",
        "Strong Bull": "\U0001f7e2",
        "Bull": "\U0001f7e9",
        "Neutral": "\u26aa",
        "Bear": "\U0001f7e5",
        "Strong Bear": "\U0001f534",
        "Extreme Bear": "\U0001f534",
    }
    return mapping.get(label, "\u26aa")


def _conviction_bar(score: int) -> str:
    """Visual bar showing conviction level 0-100."""
    filled = score // 5
    return "\u2588" * filled + "\u2591" * (20 - filled)


def build_options_digest(builder: DigestBuilder, mode: str = "facts", out_data: dict | None = None) -> str:
    """Build the options flow digest for top 3 equities by conviction.

    Args:
        builder: DigestBuilder instance with fetchers/analysis.
        mode: "facts" for data only, "full" for data + LLM commentary.
        out_data: If provided, populated with digest data for action items.
    """
    now = now_ct()
    parts = []
    analyzer = None
    digest_data = {}

    ALL_SECTIONS = ["market_snapshot", "top_convictions", "greeks_overview", "arc_outlook", "next_steps"]
    enabled = get_enabled_sections("options", ALL_SECTIONS)

    if mode == "full":
        try:
            from src.analysis.llm_analyzer import MarketAnalyzer
            analyzer = MarketAnalyzer(provider=builder.get_llm_provider())
        except Exception as e:
            logger.warning(f"Failed to init MarketAnalyzer, falling back to facts: {e}")

    # -- Header -------------------------------------------------------
    parts.append(
        f"\U0001f4ca {bold('OPTIONS FLOW DIGEST')}\n"
        f"\U0001f4c5 {esc(format_date(now, '%A, %B %d, %Y'))}\n"
        f"\U0001f550 {esc(format_time_ct(now))}"
    )

    # -- Fetch options data for all equities --------------------------
    logger.info("Fetching options flow data for equities...")
    settings = get_settings()
    us_stocks = settings.instruments.get("us_stocks", [])
    equity_symbols = [
        s.get("yfinance") or s.get("symbol", "")
        for s in us_stocks
        if s.get("enabled", True) and (s.get("yfinance") or s.get("symbol"))
    ]

    if not equity_symbols:
        parts.append(unavailable("Equity symbols"))
        if out_data is not None:
            out_data.update(digest_data)
        return "\n".join(parts)

    fetcher = OptionsFetcher()
    flow_results = []

    for sym in equity_symbols:
        try:
            chain_data = fetcher.get_option_chain(sym)
            if chain_data:
                flow = analyze_options_flow(chain_data)
                if flow:
                    # Load history for arc context
                    history = load_flow_history(sym, days=5)
                    flow["_history"] = history
                    flow["_breakdown"] = build_daily_breakdown(history)
                    flow_results.append(flow)
                    # Save snapshot
                    save_flow_snapshot(sym, flow)
        except Exception as e:
            logger.debug(f"Options flow failed for {sym}: {e}")
            continue

    if not flow_results:
        parts.append(unavailable("Options flow data"))
        if out_data is not None:
            out_data.update(digest_data)
        return "\n".join(parts)

    # Sort by conviction score descending, take top 3
    flow_results.sort(key=lambda x: x.get("conviction_score", 0), reverse=True)
    top_3 = flow_results[:3]

    digest_data["flow_results"] = top_3
    digest_data["all_results"] = flow_results

    # -- Market Snapshot ----------------------------------------------
    if "market_snapshot" in enabled:
        parts.append(section_header("\U0001f30e MARKET SNAPSHOT"))
        snapshot_lines = []
        for flow in top_3:
            sym = flow["symbol"]
            price = flow.get("stock_price", 0)
            conviction = flow.get("conviction", "?")
            score = flow.get("conviction_score", 0)
            emoji = _conviction_emoji(conviction)
            snapshot_lines.append(
                f"  {emoji} {bold(sym)}: {code(f'${price:,.2f}')} \u2014 {esc(conviction)} ({score}/100)"
            )
        parts.append("\n".join(snapshot_lines))

    # -- LLM Summary (full mode) --------------------------------------
    if analyzer and digest_data:
        try:
            summary = analyzer.analyze_section("options_summary", digest_data, context=digest_data)
            if summary:
                parts.append(analysis_block(summary))
        except Exception as e:
            logger.warning(f"Options LLM summary failed: {e}")

    # -- Top 3 Convictions (detailed) ---------------------------------
    if "top_convictions" in enabled:
        parts.append(section_header("\U0001f3af TOP 3 OPTIONS CONVICTIONS"))
        for i, flow in enumerate(top_3, 1):
            parts.append(_format_flow_pick(i, flow))

    # -- Greeks Overview -----------------------------------------------
    if "greeks_overview" in enabled:
        parts.append(section_header("\U0001f9ee GREEKS OVERVIEW"))
        for flow in top_3:
            sym = flow["symbol"]
            greeks = flow.get("greeks_summary", {})
            oi = flow.get("oi_analysis", {})
            if greeks:
                net_d = greeks.get("net_delta", 0)
                gamma = greeks.get("total_gamma", 0)
                max_pain = greeks.get("max_pain")
                put_wall = greeks.get("put_wall")
                call_wall = greeks.get("call_wall")
                pcr = oi.get("pcr_oi", 0)

                lines = [f"  {bold(sym)}:"]
                lines.append(
                    f"    Net Delta: {code(f'{net_d:+,.0f}')} | "
                    f"Gamma: {code(f'{gamma:,.0f}')}"
                )
                level_parts = []
                if max_pain:
                    level_parts.append(f"Max Pain: {code(f'${max_pain:,.2f}')}")
                if put_wall:
                    level_parts.append(f"Put Wall: {code(f'${put_wall:,.2f}')}")
                if call_wall:
                    level_parts.append(f"Call Wall: {code(f'${call_wall:,.2f}')}")
                if level_parts:
                    lines.append(f"    {' | '.join(level_parts)}")
                if pcr:
                    lines.append(f"    PCR (OI): {code(f'{pcr:.2f}')}")
                parts.append("\n".join(lines))

    # -- Arc Outlook (full mode) --------------------------------------
    if "arc_outlook" in enabled and analyzer:
        parts.append(section_header("\U0001f4c8 ARC OUTLOOK"))
        for flow in top_3:
            sym = flow["symbol"]
            history = flow.get("_history", [])
            if history:
                try:
                    from src.analysis.options_flow import generate_arc_reading
                    reading = generate_arc_reading(flow, history)
                    if reading:
                        parts.append(f"  {bold(sym)}:")
                        parts.append(analysis_block(reading))
                except Exception as e:
                    logger.debug(f"Arc reading failed for {sym}: {e}")

    # -- Next Steps (full mode) ----------------------------------------
    if "next_steps" in enabled and analyzer and digest_data:
        parts.append(section_header("\U0001f3af NEXT STEPS"))
        try:
            next_steps = analyzer.analyze_section("next_steps_options", digest_data, context=digest_data)
            if next_steps:
                parts.append(analysis_block(next_steps))
            else:
                parts.append(unavailable("Next steps"))
        except Exception as e:
            logger.warning(f"Next steps failed: {e}")
            parts.append(unavailable("Next steps"))

    # -- Footer --------------------------------------------------------
    parts.append(f"\n\n{esc(chr(9472) * 30)}\n{italic('Options flow is informational, not a trade signal.')}")

    if out_data is not None:
        out_data.update(digest_data)

    return "\n".join(parts)


def _format_flow_pick(rank: int, flow: dict) -> str:
    """Format a single options flow conviction pick for the digest."""
    sym = flow.get("symbol", "?")
    price = flow.get("stock_price", 0)
    conviction = flow.get("conviction", "?")
    score = flow.get("conviction_score", 0)
    cp_ratio = flow.get("cp_ratio", 0)
    call_prem = flow.get("total_call_premium", 0)
    put_prem = flow.get("total_put_premium", 0)
    total_prem = flow.get("total_premium", 0)
    top_call = flow.get("top_call_strike")
    top_put = flow.get("top_put_strike")

    emoji = _conviction_emoji(conviction)
    bar = _conviction_bar(score)

    # Line 1: rank, symbol, conviction
    line = f"  {rank}. {emoji} {bold(sym)} \u2014 {esc(conviction)} ({code(f'{score}/100')})"

    # Line 2: conviction bar
    line += f"\n     {code(f'[{bar}]')}"

    # Line 3: price and C/P ratio
    line += f"\n     Price: {code(f'${price:,.2f}')} | C/P Ratio: {code(f'{cp_ratio:.2f}')}"

    # Line 4: premiums
    line += (
        f"\n     Call: {code(_format_premium(call_prem))} | "
        f"Put: {code(_format_premium(put_prem))} | "
        f"Total: {code(_format_premium(total_prem))}"
    )

    # Line 5: key strikes
    strike_parts = []
    if top_call:
        strike_parts.append(f"Top Call: {code(f'${top_call:,.2f}')}")
    if top_put:
        strike_parts.append(f"Top Put: {code(f'${top_put:,.2f}')}")
    if strike_parts:
        line += f"\n     {' | '.join(strike_parts)}"

    # Line 6: daily breakdown summary (if history exists)
    breakdown = flow.get("_breakdown", [])
    if breakdown:
        recent = breakdown[:3]
        trend_parts = [f"{d['day']}: {d['sentiment']}" for d in recent]
        line += f"\n     \U0001f4c5 {esc(', '.join(trend_parts))}"

    return line
