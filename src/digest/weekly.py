"""Weekly digest template (Friday ~5:30 PM CT)."""

from src.digest.builder import DigestBuilder
from src.digest.formatter import (
    bold, code, esc, italic, section_header, price_line,
    economic_event_line, sentiment_block, analysis_block, quick_take_block,
    unavailable, comprehensive_event_line, earnings_line, forward_calendar_block,
    custom_section_block,
)
from config.settings import get_enabled_sections
from src.analysis.performance import (
    change_indicator, rank_by_performance, sector_comparison, get_top_movers,
)
from src.analysis.technicals import get_rsi_label, get_trend_emoji
from src.utils.timezone import now_ct, format_date, start_of_week_ct
from src.utils.logging_config import get_logger

logger = get_logger("weekly_digest")


def build_weekly_digest(builder: DigestBuilder, mode: str = "facts", out_data: dict | None = None) -> str:
    """Build the weekly digest message.

    Args:
        builder: DigestBuilder instance with fetchers/analysis.
        mode: "facts" for data only, "full" for data + LLM analysis.
        out_data: If provided, populated with accumulated digest data for action items.
    """
    now = now_ct()
    week_start = start_of_week_ct()
    parts = []
    analyzer = None
    digest_data = {}

    ALL_SECTIONS = ["quick_take", "week_review", "rankings", "sectors", "economic",
                    "technicals", "sentiment", "events", "next_steps"]
    enabled = get_enabled_sections("weekly", ALL_SECTIONS)

    if mode == "full":
        try:
            from src.analysis.llm_analyzer import MarketAnalyzer
            analyzer = MarketAnalyzer(provider=builder.get_llm_provider())
        except Exception as e:
            logger.warning(f"Failed to init MarketAnalyzer, falling back to facts: {e}")

    # Header
    parts.append(
        f"📊 {bold('WEEKLY MARKET DIGEST')}\n"
        f"📅 Week of {esc(format_date(week_start, '%B %d'))} — {esc(format_date(now, '%B %d, %Y'))}"
    )

    # Quick Take — placeholder, filled after data is gathered
    quick_take_index = len(parts)

    # Fetch all data
    try:
        all_prices = builder.fetch_all_prices()
    except Exception as e:
        logger.error(f"Price fetch failed: {e}")
        all_prices = {}

    try:
        technicals = builder.run_technicals()
    except Exception:
        technicals = {}

    # Build instruments list with weekly changes
    instruments = []
    for sym, data in all_prices.items():
        inst = {**data, "symbol": sym}
        # Use daily change_pct as approximation; ideally would compare Mon open vs Fri close
        inst["weekly_change_pct"] = data.get("change_pct", 0)
        instruments.append(inst)

    # 1. Week-in-Review Narrative
    if "week_review" in enabled:
        parts.append(section_header("📝 WEEK IN REVIEW"))
        try:
            if instruments:
                movers = get_top_movers(instruments, n=3)
                gainers = movers.get("gainers", [])
                losers = movers.get("losers", [])

                narrative_parts = []
                if gainers:
                    g_names = ", ".join(g.get("name", "") for g in gainers[:3])
                    narrative_parts.append(f"Top performers: {esc(g_names)}")
                if losers:
                    l_names = ", ".join(l.get("name", "") for l in losers[:3])
                    narrative_parts.append(f"Laggards: {esc(l_names)}")

                vix = all_prices.get("VIX", {})
                if vix:
                    vix_val = vix.get("price", 0)
                    narrative_parts.append(f"VIX at {code(f'{vix_val:.1f}')}")

                parts.append("  " + " | ".join(narrative_parts))

                if analyzer:
                    digest_data["week_review"] = all_prices
                    analysis = analyzer.analyze_section("week_review", all_prices, context=digest_data)
                    if analysis:
                        parts.append(analysis_block(analysis))
            else:
                parts.append(unavailable("Week summary"))
        except Exception as e:
            logger.warning(f"Narrative failed: {e}")
            parts.append(unavailable("Week summary"))

    # 2. Weekly Performance Rankings
    if "rankings" in enabled:
        parts.append(section_header("🏆 WEEKLY PERFORMANCE RANKINGS"))
        try:
            ranked = rank_by_performance(instruments, key="change_pct")
            if ranked:
                for i, inst in enumerate(ranked[:15], 1):
                    name = inst.get("name", inst.get("symbol", "?"))
                    chg = inst.get("change_pct", 0)
                    price = inst.get("price", 0)
                    parts.append(f"  {i:2d}. {bold(name)}  {code(f'{price:,.2f}')}  {change_indicator(chg)}")
                if len(ranked) > 15:
                    parts.append(f"  {italic(f'... and {len(ranked) - 15} more')}")

                if analyzer:
                    digest_data["rankings"] = ranked
                    analysis = analyzer.analyze_section("rankings", ranked, context=digest_data)
                    if analysis:
                        parts.append(analysis_block(analysis))
            else:
                parts.append(unavailable("Rankings"))
        except Exception as e:
            logger.warning(f"Rankings failed: {e}")
            parts.append(unavailable("Rankings"))

    # 3. Sector Comparison
    if "sectors" in enabled:
        parts.append(section_header("📊 SECTOR COMPARISON"))
        try:
            sectors = sector_comparison(instruments)
            if sectors:
                for s in sectors:
                    sector_name = s["sector"].replace("_", " ").title()
                    parts.append(
                        f"  {esc(sector_name):18s} {change_indicator(s['avg_change_pct']):>15s}\n"
                        f"    Best: {esc(s['best']['name'])} ({change_indicator(s['best']['change_pct'])})\n"
                        f"    Worst: {esc(s['worst']['name'])} ({change_indicator(s['worst']['change_pct'])})"
                    )

                if analyzer:
                    digest_data["sectors"] = sectors
                    analysis = analyzer.analyze_section("sectors", sectors, context=digest_data)
                    if analysis:
                        parts.append(analysis_block(analysis))
            else:
                parts.append(unavailable("Sector data"))
        except Exception as e:
            logger.warning(f"Sector comparison failed: {e}")
            parts.append(unavailable("Sector data"))

    # 4. Economic Data Recap
    if "economic" in enabled:
        parts.append(section_header("📈 ECONOMIC DATA RECAP"))
        try:
            econ = builder.fetch_economic_data()
            if econ:
                for series_id, data in econ.items():
                    name = data.get("name", series_id)
                    value = data.get("value", 0)
                    prev = data.get("prev_value", 0)
                    date = data.get("date", "")
                    parts.append(
                        f"  {esc(name)}: {code(f'{value:.2f}')} "
                        f"(prev: {code(f'{prev:.2f}')}, as of {esc(date)})"
                    )

                spread = builder.fetch_yield_spread()
                if spread:
                    inv = " ⚠️ INVERTED" if spread["inverted"] else ""
                    spread_val = spread['spread']
                    parts.append(
                        f"\n  10Y-2Y Spread: {code(f'{spread_val:.2f}%')}{inv}"
                    )

                if analyzer:
                    digest_data["economic"] = {"econ": econ, "spread": spread}
                    analysis = analyzer.analyze_section("economic", {"econ": econ, "spread": spread}, context=digest_data)
                    if analysis:
                        parts.append(analysis_block(analysis))
            else:
                parts.append(unavailable("Economic data"))
        except Exception as e:
            logger.warning(f"Economic data failed: {e}")
            parts.append(unavailable("Economic data"))

    # 5. Technical Outlook
    if "technicals" in enabled:
        parts.append(section_header("🔧 TECHNICAL OUTLOOK"))
        try:
            if technicals:
                for sym, ta in list(technicals.items())[:15]:
                    name = ta.get("name", sym)
                    rsi = ta.get("rsi")
                    trend = ta.get("trend", "N/A")
                    emoji = ta.get("trend_emoji", "")
                    rsi_str = f"RSI: {code(f'{rsi:.0f}')} ({esc(get_rsi_label(rsi))})" if rsi else "RSI: N/A"
                    parts.append(f"  {emoji} {esc(name):18s} {rsi_str}  Trend: {esc(trend)}")

                if analyzer:
                    digest_data["technicals"] = technicals
                    analysis = analyzer.analyze_section("technicals", technicals, context=digest_data)
                    if analysis:
                        parts.append(analysis_block(analysis))
            else:
                parts.append(unavailable("Technical outlook"))
        except Exception as e:
            logger.warning(f"Technical outlook failed: {e}")
            parts.append(unavailable("Technical outlook"))

    # 6. Sentiment
    if "sentiment" in enabled:
        parts.append(section_header("🧭 WEEKLY SENTIMENT"))
        try:
            sentiment = builder.compute_sentiment(prices=all_prices, technicals=technicals)
            parts.append(sentiment_block(sentiment))

            if analyzer:
                digest_data["sentiment"] = sentiment
                analysis = analyzer.analyze_section("sentiment", sentiment, context=digest_data)
                if analysis:
                    parts.append(analysis_block(analysis))
        except Exception as e:
            logger.warning(f"Sentiment failed: {e}")
            parts.append(unavailable("Sentiment"))

    # 7. Week in Review — Events
    comp_events_week = {}
    comp_events_next = {}
    if "events" in enabled:
        parts.append(section_header("📅 WEEK IN REVIEW — EVENTS"))
        try:
            comp_events_week = builder.fetch_comprehensive_events(scope="week")
            econ_this_week = comp_events_week.get("economic_events", [])
            bell_this_week = comp_events_week.get("earnings_bellwether", [])

            if econ_this_week:
                for event in econ_this_week[:10]:
                    parts.append(comprehensive_event_line(event))
            else:
                parts.append(f"  {esc('No major US economic events this week')}")

            if bell_this_week:
                parts.append(f"\n  {bold('Bellwether Earnings This Week')}")
                for e in bell_this_week[:8]:
                    parts.append(earnings_line(e))
                other_count = comp_events_week.get("earnings_other_count", 0)
                if other_count > 0:
                    parts.append(f"  {italic(f'+ {other_count} more reported this week')}")

            if analyzer:
                digest_data["events"] = comp_events_week
                analysis = analyzer.analyze_events(comp_events_week, context=digest_data)
                if analysis:
                    parts.append(analysis_block(analysis))
        except Exception as e:
            logger.warning(f"Week events failed: {e}")
            parts.append(unavailable("Week events"))

        # 7b. Looking Ahead — Next Week + Forward Calendar
        parts.append(section_header("📆 LOOKING AHEAD"))
        try:
            comp_events_next = builder.fetch_comprehensive_events(scope="next_week")
            next_econ = comp_events_next.get("economic_events", [])
            next_bell = comp_events_next.get("earnings_bellwether", [])

            if next_econ:
                parts.append(f"  {bold('Next Week Economic Events')}")
                for event in next_econ[:8]:
                    parts.append(comprehensive_event_line(event))

            if next_bell:
                parts.append(f"\n  {bold('Next Week Bellwether Earnings')}")
                for e in next_bell[:6]:
                    parts.append(earnings_line(e))
                next_other = comp_events_next.get("earnings_other_count", 0)
                if next_other > 0:
                    parts.append(f"  {italic(f'+ {next_other} more reporting next week')}")

            # Forward calendar (FOMC, etc.)
            forward = comp_events_next.get("forward_calendar", [])
            if forward:
                parts.append(f"\n  {bold('Key Dates Ahead')}")
                parts.append(forward_calendar_block(forward))

            if not next_econ and not next_bell and not forward:
                parts.append(f"  {esc('No major events scheduled next week')}")
        except Exception as e:
            logger.warning(f"Looking ahead failed: {e}")
            parts.append(unavailable("Looking ahead"))

    # Quick Take — generate now that we have all data, insert near top
    if "quick_take" in enabled:
        try:
            from src.analysis.events import get_forward_calendar

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
                # Top movers
                if instruments:
                    top_movers = get_top_movers(instruments, n=1)
                    gainer = (top_movers.get("gainers") or [None])[0]
                    loser = (top_movers.get("losers") or [None])[0]
                    if gainer:
                        qt_lines.append(f"  Bullish: {esc(gainer.get('name', '?'))} led the week at {gainer.get('change_pct', 0):+.2f}%")
                    if loser:
                        qt_lines.append(f"  Bearish: {esc(loser.get('name', '?'))} weakest at {loser.get('change_pct', 0):+.2f}%")
                # FOMC countdown
                fomc = get_forward_calendar()
                if fomc:
                    qt_lines.append(f"  Event: FOMC Rate Decision {esc(fomc[0]['formatted'])}")
                # Bellwether earnings next week
                if comp_events_next.get("earnings_bellwether"):
                    syms = ", ".join(e["symbol"] for e in comp_events_next["earnings_bellwether"][:3])
                    qt_lines.append(f"  Earnings: Next week bellwether — {esc(syms)}")
                if qt_lines:
                    quick_take_parts.extend(qt_lines)
                else:
                    quick_take_parts.append(f"  {esc('No major highlights to flag')}")

            parts.insert(quick_take_index + 1, "\n".join(quick_take_parts))
        except Exception as e:
            logger.warning(f"Quick Take failed: {e}")

    # 8. Custom Data Sources
    try:
        custom_sources = builder.fetch_custom_sources("weekly")
        for src_id, src_info in custom_sources.items():
            cfg = src_info["config"]
            integration = cfg.get("digest_integration", {})
            if integration.get("mode") == "section":
                title = integration.get("section_title", cfg.get("name", src_id))
                parts.append(section_header(f"\U0001f4cc {title}"))
                parts.append(custom_section_block(title, src_info["data"], cfg.get("type", "http")))
    except Exception as e:
        logger.warning(f"Custom sources failed: {e}")

    # 9. Next Week — Key Themes
    if "next_steps" in enabled and analyzer and digest_data:
        parts.append(section_header("🎯 NEXT WEEK — KEY THEMES"))
        try:
            next_steps = analyzer.analyze_next_steps("weekly", digest_data)
            if next_steps:
                parts.append(analysis_block(next_steps))
            else:
                parts.append(unavailable("Next week themes"))
        except Exception as e:
            logger.warning(f"Next week themes failed: {e}")
            parts.append(unavailable("Next week themes"))

    # Footer
    parts.append(f"\n\n{esc('─' * 30)}\n{italic('Have a great weekend!')}")

    # Save retrace snapshot
    try:
        from src.retrace.snapshot import save_snapshot
        from src.retrace.versioning import get_current_version_id
        save_snapshot(digest_data, {}, get_current_version_id("prompts") or "unversioned",
                      digest_type="weekly")
    except Exception as e:
        logger.warning(f"Retrace snapshot save failed: {e}")

    if out_data is not None:
        out_data.update(digest_data)

    return "\n".join(parts)
