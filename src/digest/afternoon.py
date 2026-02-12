"""Afternoon digest template (~4:30 PM CT, Mon-Fri)."""

from src.digest.builder import DigestBuilder
from src.digest.formatter import (
    bold, code, esc, italic, section_header, price_line, forex_line,
    commodity_line, index_line, economic_event_line, sentiment_block,
    movers_block, analysis_block, quick_take_block, unavailable,
    comprehensive_event_line, earnings_line, forward_calendar_block,
    custom_section_block,
)
from config.settings import get_enabled_sections
from src.analysis.performance import change_indicator, get_top_movers
from src.analysis.sentiment import get_sentiment_emoji
from src.analysis.events import get_forward_calendar
from src.utils.timezone import now_ct, format_date, format_time_ct
from src.utils.logging_config import get_logger

logger = get_logger("afternoon_digest")


def build_afternoon_digest(builder: DigestBuilder, mode: str = "facts", out_data: dict | None = None) -> str:
    """Build the afternoon digest message.

    Args:
        builder: DigestBuilder instance with fetchers/analysis.
        mode: "facts" for data only, "full" for data + LLM analysis.
        out_data: If provided, populated with accumulated digest data for action items.
    """
    now = now_ct()
    parts = []
    analyzer = None
    digest_data = {}

    ALL_SECTIONS = ["quick_take", "indices_close", "forex", "commodities",
                    "crypto", "sentiment_shift", "movers", "events", "next_steps"]
    enabled = get_enabled_sections("afternoon", ALL_SECTIONS)

    if mode == "full":
        try:
            from src.analysis.llm_analyzer import MarketAnalyzer
            analyzer = MarketAnalyzer(provider=builder.get_llm_provider())
        except Exception as e:
            logger.warning(f"Failed to init MarketAnalyzer, falling back to facts: {e}")

    # Header
    parts.append(
        f"🌆 {bold('AFTERNOON MARKET DIGEST')}\n"
        f"📅 {esc(format_date(now, '%A, %B %d, %Y'))}\n"
        f"🕐 {esc(format_time_ct(now))}"
    )

    # Quick Take — placeholder, filled after data is gathered
    quick_take_index = len(parts)

    # Hoist all_prices fetch — used by indices_close, sentiment_shift, movers
    try:
        all_prices = builder.fetch_all_prices()
    except Exception as e:
        logger.warning(f"Price fetch failed: {e}")
        all_prices = {}

    # 1. US Indices Closing Recap
    if "indices_close" in enabled:
        parts.append(section_header("📈 US INDICES — CLOSING RECAP"))
        try:
            indices = {k: v for k, v in all_prices.items() if v.get("category") == "us_index"}
            if indices:
                for sym, data in indices.items():
                    parts.append(index_line(data["name"], data["price"], data["change_pct"]))

                if analyzer:
                    digest_data["indices_close"] = indices
                    analysis = analyzer.analyze_section("indices_close", indices, context=digest_data)
                    if analysis:
                        parts.append(analysis_block(analysis))
            else:
                parts.append(unavailable("US Indices"))
        except Exception as e:
            logger.warning(f"Indices fetch failed: {e}")
            parts.append(unavailable("US Indices"))

    # 2. Forex Daily Ranges
    if "forex" in enabled:
        parts.append(section_header("💱 FOREX — DAILY SESSION"))
        try:
            forex = builder.fetch_forex_prices()
            if forex:
                for sym, data in forex.items():
                    if sym == "DXY":
                        continue
                    price_val = data.get('price', 0)
                    low_val = data.get('low', 0)
                    high_val = data.get('high', 0)
                    line = (
                        f"  {esc(data['name'])}: {code(f'{price_val:.5f}')}  "
                        f"{change_indicator(data.get('change_pct', 0))}\n"
                        f"    Range: {code(f'{low_val:.5f}')} — {code(f'{high_val:.5f}')}"
                    )
                    parts.append(line)

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

    # 3. Commodities Daily Close
    if "commodities" in enabled:
        parts.append(section_header("🏗️ COMMODITIES — DAILY CLOSE"))
        try:
            commodities = builder.fetch_commodity_prices()
            if commodities:
                for sym, data in commodities.items():
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

    # 4. Crypto
    if "crypto" in enabled:
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

    # 5. Sentiment Shift (morning vs close)
    if "sentiment_shift" in enabled:
        parts.append(section_header("🧭 SENTIMENT SHIFT"))
        try:
            technicals = builder.run_technicals()
            digest_data["technicals"] = technicals
            current_sentiment = builder.compute_sentiment(prices=all_prices, technicals=technicals)
            morning_snapshot = builder.get_morning_snapshot()

            parts.append(sentiment_block(current_sentiment))

            if morning_snapshot:
                morning_score = morning_snapshot.get("sentiment", {}).get("composite_score", 50)
                current_score = current_sentiment.get("composite_score", 50)
                shift = current_score - morning_score
                direction = "improved" if shift > 0 else "deteriorated" if shift < 0 else "unchanged"
                parts.append(
                    f"\n  Morning → Close: {code(str(morning_score))} → {code(str(current_score))} "
                    f"({'+' if shift > 0 else ''}{shift} pts, {esc(direction)})"
                )

            if analyzer:
                digest_data["sentiment_shift"] = current_sentiment
                analysis = analyzer.analyze_section("sentiment_shift", current_sentiment, context=digest_data)
                if analysis:
                    parts.append(analysis_block(analysis))
        except Exception as e:
            logger.warning(f"Sentiment failed: {e}")
            parts.append(unavailable("Sentiment"))

    # 5b. Key Movers
    if "movers" in enabled:
        parts.append(section_header("🔥 KEY MOVERS"))
        try:
            all_instruments = [
                {**v, "symbol": k}
                for k, v in all_prices.items()
                if v.get("change_pct") is not None
            ]
            if all_instruments:
                movers = get_top_movers(all_instruments, n=5)
                parts.append(movers_block(movers))

                if analyzer:
                    digest_data["movers"] = movers
                    analysis = analyzer.analyze_section("movers", movers, context=digest_data)
                    if analysis:
                        parts.append(analysis_block(analysis))
            else:
                parts.append(unavailable("Movers"))
        except Exception as e:
            logger.warning(f"Movers failed: {e}")
            parts.append(unavailable("Movers"))

    # 6. Today's Results & Tomorrow Preview
    comp_events = {}
    if "events" in enabled:
        parts.append(section_header("📅 TODAY'S RESULTS & TOMORROW"))
        try:
            # Today's results
            today_events = builder.fetch_comprehensive_events(scope="today")
            today_econ = today_events.get("economic_events", [])
            if today_econ:
                parts.append(f"  {bold('Today')}")
                for event in today_econ[:6]:
                    parts.append(comprehensive_event_line(event))

            # Tomorrow preview
            tmrw_events = builder.fetch_comprehensive_events(scope="tomorrow")
            tmrw_econ = tmrw_events.get("economic_events", [])
            if tmrw_econ:
                parts.append(f"\n  {bold('Tomorrow')}")
                for event in tmrw_econ[:6]:
                    parts.append(comprehensive_event_line(event))

            # Merge for LLM context
            comp_events = {
                "economic_events": today_econ + tmrw_econ,
                "earnings_bellwether": today_events.get("earnings_bellwether", []) + tmrw_events.get("earnings_bellwether", []),
                "earnings_other_count": today_events.get("earnings_other_count", 0) + tmrw_events.get("earnings_other_count", 0),
                "earnings_total": today_events.get("earnings_total", 0) + tmrw_events.get("earnings_total", 0),
                "forward_calendar": tmrw_events.get("forward_calendar", []),
            }

            # Tomorrow's bellwether earnings
            tmrw_bell = tmrw_events.get("earnings_bellwether", [])
            if tmrw_bell:
                parts.append(f"\n  {bold('Tomorrow Bellwether Earnings')}")
                for e in tmrw_bell[:6]:
                    parts.append(earnings_line(e))
                tmrw_other = tmrw_events.get("earnings_other_count", 0)
                if tmrw_other > 0:
                    parts.append(f"  {italic(f'+ {tmrw_other} more reporting tomorrow')}")

            if not today_econ and not tmrw_econ and not tmrw_bell:
                parts.append(f"  {esc('No major US events today or tomorrow')}")

            # Forward calendar
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

    # Quick Take — generate now that we have all data, insert near top
    if "quick_take" in enabled:
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
                # Biggest index move
                if digest_data.get("indices_close"):
                    biggest = max(digest_data["indices_close"].items(),
                                  key=lambda x: abs(x[1].get("change_pct", 0) or 0),
                                  default=None)
                    if biggest:
                        sym, d = biggest
                        chg = d.get("change_pct", 0) or 0
                        prefix = "Bullish:" if chg > 0 else "Bearish:"
                        qt_lines.append(f"  {prefix} {esc(d.get('name', sym))} closed {'+' if chg > 0 else ''}{chg:.2f}%")
                # FOMC countdown
                fomc = get_forward_calendar()
                if fomc:
                    qt_lines.append(f"  Event: FOMC Rate Decision {esc(fomc[0]['formatted'])}")
                # Bellwether earnings (deduplicated)
                if comp_events.get("earnings_bellwether"):
                    seen = set()
                    unique_syms = []
                    for e in comp_events["earnings_bellwether"]:
                        s = e["symbol"]
                        if s not in seen:
                            seen.add(s)
                            unique_syms.append(s)
                        if len(unique_syms) >= 3:
                            break
                    qt_lines.append(f"  Earnings: Bellwether reports — {esc(', '.join(unique_syms))}")
                if qt_lines:
                    quick_take_parts.extend(qt_lines)
                else:
                    quick_take_parts.append(f"  {esc('No major highlights to flag')}")

            parts.insert(quick_take_index + 1, "\n".join(quick_take_parts))
        except Exception as e:
            logger.warning(f"Quick Take failed: {e}")

    # 7. Custom Data Sources
    try:
        custom_sources = builder.fetch_custom_sources("afternoon")
        for src_id, src_info in custom_sources.items():
            cfg = src_info["config"]
            integration = cfg.get("digest_integration", {})
            if integration.get("mode") == "section":
                title = integration.get("section_title", cfg.get("name", src_id))
                parts.append(section_header(f"\U0001f4cc {title}"))
                parts.append(custom_section_block(title, src_info["data"], cfg.get("type", "http")))
    except Exception as e:
        logger.warning(f"Custom sources failed: {e}")

    # 8. Next Steps
    if "next_steps" in enabled and analyzer and digest_data:
        parts.append(section_header("🎯 NEXT STEPS"))
        try:
            next_steps = analyzer.analyze_next_steps("afternoon", digest_data)
            if next_steps:
                parts.append(analysis_block(next_steps))
            else:
                parts.append(unavailable("Next steps"))
        except Exception as e:
            logger.warning(f"Next steps failed: {e}")
            parts.append(unavailable("Next steps"))

    # Footer
    parts.append(f"\n\n{esc('─' * 30)}\n{italic('Markets closed. See you tomorrow!')}")

    # Save retrace snapshot
    try:
        from src.retrace.snapshot import save_snapshot
        from src.retrace.versioning import get_current_version_id
        save_snapshot(digest_data, {}, get_current_version_id("prompts") or "unversioned",
                      digest_type="afternoon")
    except Exception as e:
        logger.warning(f"Retrace snapshot save failed: {e}")

    if out_data is not None:
        out_data.update(digest_data)

    return "\n".join(parts)
