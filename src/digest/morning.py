"""Morning digest template (~6:30 AM CT, Mon-Fri)."""

from src.digest.builder import DigestBuilder
from src.digest.formatter import (
    bold, code, esc, italic, section_header, price_line, forex_line,
    commodity_line, index_line, economic_event_line, sentiment_block,
    session_block, analysis_block, quick_take_block, unavailable,
    comprehensive_event_line, earnings_line, forward_calendar_block,
)
from src.analysis.performance import change_indicator
from src.analysis.events import get_forward_calendar
from src.utils.timezone import now_ct, format_date, format_time_ct
from src.utils.logging_config import get_logger

logger = get_logger("morning_digest")


def build_morning_digest(builder: DigestBuilder, mode: str = "facts", out_data: dict | None = None) -> str:
    """Build the morning digest message.

    Args:
        builder: DigestBuilder instance with fetchers/analysis.
        mode: "facts" for data only, "full" for data + LLM analysis.
        out_data: If provided, populated with accumulated digest data for action items.
    """
    now = now_ct()
    parts = []
    analyzer = None
    digest_data = {}

    if mode == "full":
        try:
            from src.analysis.llm_analyzer import MarketAnalyzer
            analyzer = MarketAnalyzer(provider=builder.get_llm_provider())
        except Exception as e:
            logger.warning(f"Failed to init MarketAnalyzer, falling back to facts: {e}")

    # Header
    parts.append(
        f"☀️ {bold('MORNING MARKET DIGEST')}\n"
        f"📅 {esc(format_date(now, '%A, %B %d, %Y'))}\n"
        f"🕐 {esc(format_time_ct(now))}"
    )

    # Quick Take — placeholder, filled after data is gathered
    quick_take_index = len(parts)

    # 1. Overnight Recap
    parts.append(section_header("🌙 OVERNIGHT RECAP"))
    try:
        overnight = builder.fetch_overnight_data()
        sydney_data = overnight.get("sydney", {})
        tokyo_data = overnight.get("tokyo", {})

        if sydney_data or tokyo_data:
            if sydney_data:
                parts.append(session_block("sydney", sydney_data))
            if tokyo_data:
                parts.append(session_block("tokyo", tokyo_data))

            if analyzer:
                combined = {}
                combined.update(sydney_data)
                combined.update(tokyo_data)
                digest_data["overnight"] = combined
                analysis = analyzer.analyze_section("overnight", combined, context=digest_data)
                if analysis:
                    parts.append(analysis_block(analysis))
        else:
            parts.append(unavailable("Overnight sessions"))
    except Exception as e:
        logger.warning(f"Overnight recap failed: {e}")
        parts.append(unavailable("Overnight sessions"))

    # 2. US Futures Pre-Market
    parts.append(section_header("📊 US FUTURES PRE-MARKET"))
    try:
        futures = builder.fetch_futures_prices()
        if futures:
            for sym, data in futures.items():
                parts.append(index_line(data["name"], data["price"], data["change_pct"]))

            if analyzer:
                digest_data["futures"] = futures
                analysis = analyzer.analyze_section("futures", futures, context=digest_data)
                if analysis:
                    parts.append(analysis_block(analysis))
        else:
            parts.append(unavailable("Futures"))
    except Exception as e:
        logger.warning(f"Futures fetch failed: {e}")
        parts.append(unavailable("Futures"))

    # 3. Forex Major Pairs with Pivots
    parts.append(section_header("💱 FOREX MAJORS"))
    try:
        forex = builder.fetch_forex_prices()
        pivots = builder.fetch_forex_pivots()

        if forex:
            for sym, data in forex.items():
                if sym == "DXY":
                    continue
                pair_pivots = pivots.get(sym)
                parts.append(forex_line(data["name"], data["price"], data["change_pct"], pair_pivots))

            if analyzer:
                digest_data["forex"] = forex
                analysis = analyzer.analyze_section("forex", forex, context=digest_data)
                if analysis:
                    parts.append(analysis_block(analysis))
        else:
            parts.append(unavailable("Forex"))
    except Exception as e:
        logger.warning(f"Forex fetch failed: {e}")
        parts.append(unavailable("Forex"))

    # 4. Commodities Snapshot
    parts.append(section_header("🏗️ COMMODITIES"))
    try:
        commodities = builder.fetch_commodity_prices()
        if commodities:
            # Group by subcategory
            metals = {k: v for k, v in commodities.items() if v.get("category") == "metals"}
            energy = {k: v for k, v in commodities.items() if v.get("category") == "energy"}
            agri = {k: v for k, v in commodities.items() if v.get("category") == "agriculture"}

            if metals:
                parts.append(f"  {bold('Metals')}")
                for sym, data in metals.items():
                    parts.append(commodity_line(data["name"], data["price"], data["change_pct"]))
            if energy:
                parts.append(f"  {bold('Energy')}")
                for sym, data in energy.items():
                    parts.append(commodity_line(data["name"], data["price"], data["change_pct"]))
            if agri:
                parts.append(f"  {bold('Agriculture')}")
                for sym, data in agri.items():
                    parts.append(commodity_line(data["name"], data["price"], data["change_pct"]))

            if analyzer:
                digest_data["commodities"] = commodities
                analysis = analyzer.analyze_section("commodities", commodities, context=digest_data)
                if analysis:
                    parts.append(analysis_block(analysis))
        else:
            parts.append(unavailable("Commodities"))
    except Exception as e:
        logger.warning(f"Commodities fetch failed: {e}")
        parts.append(unavailable("Commodities"))

    # 5. Crypto
    parts.append(section_header("🪙 CRYPTO"))
    try:
        crypto = builder.fetch_crypto_prices()
        if crypto:
            for sym, data in crypto.items():
                parts.append(price_line(data["name"], data["price"], data["change_pct"]))

            if analyzer:
                digest_data["crypto"] = crypto
                analysis = analyzer.analyze_section("crypto", crypto, context=digest_data)
                if analysis:
                    parts.append(analysis_block(analysis))
        else:
            parts.append(unavailable("Crypto"))
    except Exception as e:
        logger.warning(f"Crypto fetch failed: {e}")
        parts.append(unavailable("Crypto"))

    # 6. This Week's Events (Economic + Earnings + Forward Calendar)
    parts.append(section_header("📅 THIS WEEK'S EVENTS"))
    try:
        comp_events = builder.fetch_comprehensive_events(scope="week")
        econ_events = comp_events.get("economic_events", [])
        bellwether = comp_events.get("earnings_bellwether", [])
        other_count = comp_events.get("earnings_other_count", 0)

        if econ_events:
            for event in econ_events[:10]:
                parts.append(comprehensive_event_line(event))
        else:
            parts.append(f"  {esc('No major US economic events this week')}")

        # Bellwether earnings
        if bellwether:
            parts.append(f"\n  {bold('Bellwether Earnings')}")
            for e in bellwether[:8]:
                parts.append(earnings_line(e))
            if other_count > 0:
                parts.append(f"  {italic(f'+ {other_count} more reporting this week')}")

        # Forward calendar (FOMC countdown)
        forward = comp_events.get("forward_calendar", [])
        if forward:
            parts.append(f"\n  {bold('Looking Ahead')}")
            parts.append(forward_calendar_block(forward))

        if analyzer:
            digest_data["events"] = comp_events
            analysis = analyzer.analyze_events(comp_events, context=digest_data)
            if analysis:
                parts.append(analysis_block(analysis))
    except Exception as e:
        logger.warning(f"Events section failed: {e}")
        parts.append(unavailable("Events"))

    # 7. Sentiment Overview
    parts.append(section_header("🧭 MARKET SENTIMENT"))
    try:
        all_prices = builder.fetch_all_prices()
        technicals = builder.run_technicals()
        digest_data["technicals"] = technicals
        sentiment = builder.compute_sentiment(prices=all_prices, technicals=technicals)
        parts.append(sentiment_block(sentiment))

        # DXY line
        dxy = all_prices.get("DXY")
        if dxy and dxy.get("price") and dxy["price"] == dxy["price"]:  # guard nan
            dxy_price = dxy['price']
            dxy_chg = dxy.get('change_pct', 0) or 0
            parts.append(f"\n  DXY: {code(f'{dxy_price:.2f}')}  {change_indicator(dxy_chg)}")

        if analyzer:
            digest_data["sentiment"] = sentiment
            analysis = analyzer.analyze_section("sentiment", sentiment, context=digest_data)
            if analysis:
                parts.append(analysis_block(analysis))

        # Save snapshot for afternoon comparison
        builder.save_morning_snapshot(sentiment, all_prices)
    except Exception as e:
        logger.warning(f"Sentiment failed: {e}")
        parts.append(unavailable("Sentiment"))

    # Quick Take — generate now that we have all data, insert near top
    try:
        quick_take_parts = []
        quick_take_parts.append(section_header("⚡ QUICK TAKE"))
        if analyzer and digest_data:
            qt = analyzer.generate_quick_take(digest_data)
            if qt:
                quick_take_parts.append(quick_take_block(qt))
            else:
                quick_take_parts.append(unavailable("Quick Take"))
        else:
            # Facts mode: algorithmic fallback
            qt_lines = []
            # Biggest futures move
            if digest_data.get("futures"):
                biggest = max(digest_data["futures"].items(),
                              key=lambda x: abs(x[1].get("change_pct", 0) or 0),
                              default=None)
                if biggest:
                    sym, d = biggest
                    chg = d.get("change_pct", 0) or 0
                    prefix = "Bullish:" if chg > 0 else "Bearish:"
                    qt_lines.append(f"  {prefix} {esc(d.get('name', sym))} futures {'+' if chg > 0 else ''}{chg:.2f}%")
            # FOMC countdown
            fomc = get_forward_calendar()
            if fomc:
                qt_lines.append(f"  Event: FOMC Rate Decision {esc(fomc[0]['formatted'])}")
            # Bellwether earnings
            if comp_events.get("earnings_bellwether"):
                syms = ", ".join(e["symbol"] for e in comp_events["earnings_bellwether"][:3])
                qt_lines.append(f"  Earnings: Bellwether reports this week — {esc(syms)}")
            if qt_lines:
                quick_take_parts.extend(qt_lines)
            else:
                quick_take_parts.append(f"  {esc('No major highlights to flag')}")

        parts.insert(quick_take_index + 1, "\n".join(quick_take_parts))
    except Exception as e:
        logger.warning(f"Quick Take failed: {e}")

    # 8. Next Steps
    if analyzer and digest_data:
        parts.append(section_header("🎯 NEXT STEPS"))
        try:
            next_steps = analyzer.analyze_next_steps("morning", digest_data)
            if next_steps:
                parts.append(analysis_block(next_steps))
            else:
                parts.append(unavailable("Next steps"))
        except Exception as e:
            logger.warning(f"Next steps failed: {e}")
            parts.append(unavailable("Next steps"))

    # Footer
    parts.append(f"\n\n{esc('─' * 30)}\n{italic('Good morning & good trading!')}")

    if out_data is not None:
        out_data.update(digest_data)

    return "\n".join(parts)
