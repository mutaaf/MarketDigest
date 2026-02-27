"""Day Trade Picks digest — pre-market ranked instrument picks."""

from src.digest.builder import DigestBuilder
from src.digest.formatter import (
    bold, code, esc, italic, section_header, analysis_block, unavailable,
    enhanced_pick_line, custom_section_block,
)
from config.settings import get_enabled_sections
from src.analysis.technicals import full_analysis, get_trend_emoji, weekly_full_analysis, monthly_full_analysis
from src.analysis.daytrade_scorer import score_instrument, rank_daytrade_picks, get_condensed_track_record
from src.analysis.multi_tf_scorer import score_instrument_swing, score_instrument_longterm
from src.analysis.fundamentals import fetch_fundamentals, score_fundamentals, is_equity_symbol
from src.analysis.performance import change_indicator
from src.utils.timezone import now_ct, format_date, format_time_ct
from src.utils.logging_config import get_logger

logger = get_logger("daytrade_digest")


def build_daytrade_digest(builder: DigestBuilder, mode: str = "facts", out_data: dict | None = None) -> str:
    """Build the day trade picks digest.

    Args:
        builder: DigestBuilder instance with fetchers/analysis.
        mode: "facts" for algorithmic only, "full" for data + LLM thesis.
        out_data: If provided, populated with accumulated digest data for action items.
    """
    now = now_ct()
    parts = []
    analyzer = None
    digest_data = {}

    ALL_SECTIONS = ["market_conditions", "top_picks", "honorable_mentions",
                    "avoid_list", "next_steps"]
    enabled = get_enabled_sections("daytrade", ALL_SECTIONS)

    if mode == "full":
        try:
            from src.analysis.llm_analyzer import MarketAnalyzer
            analyzer = MarketAnalyzer(provider=builder.get_llm_provider())
        except Exception as e:
            logger.warning(f"Failed to init MarketAnalyzer, falling back to facts: {e}")

    # ── Header ──────────────────────────────────────────────────
    parts.append(
        f"\U0001f514 {bold('US MARKET OPEN — DAY TRADE PICKS')}\n"
        f"\U0001f4c5 {esc(format_date(now, '%A, %B %d, %Y'))}\n"
        f"\U0001f550 {esc(format_time_ct(now))}"
    )

    # ── Fetch all data ──────────────────────────────────────────
    logger.info("Fetching daytrade universe prices...")
    prices = builder.fetch_daytrade_universe()

    if not prices:
        parts.append(unavailable("Price data"))
        if out_data is not None:
            out_data.update(digest_data)
        return "\n".join(parts)

    # ── Market conditions ───────────────────────────────────────
    if "market_conditions" in enabled:
        parts.append(section_header("\U0001f30d MARKET CONDITIONS"))
        try:
            vix_data = prices.get("VIX", {})
            es_data = prices.get("ES", {})
            nq_data = prices.get("NQ", {})

            vix_price = vix_data.get("price")
            vix_label = "Low" if vix_price and vix_price < 15 else "Normal" if vix_price and vix_price < 25 else "Elevated" if vix_price else "N/A"

            # Sentiment from builder
            sentiment = None
            try:
                technicals_data = builder.run_technicals()
                sentiment = builder.compute_sentiment(prices=prices, technicals=technicals_data)
                digest_data["sentiment"] = sentiment
            except Exception:
                pass

            cond_lines = []
            if vix_price:
                cond_lines.append(f"VIX: {code(f'{vix_price:.1f}')} ({esc(vix_label)})")
            if es_data.get("change_pct") is not None:
                cond_lines.append(f"ES Futures: {change_indicator(es_data['change_pct'])}")
            if nq_data.get("change_pct") is not None:
                cond_lines.append(f"NQ Futures: {change_indicator(nq_data['change_pct'])}")
            if sentiment and sentiment.get("composite_score"):
                score = sentiment["composite_score"]
                label = sentiment.get("classification", "")
                cond_lines.append(f"Sentiment: {code(f'{score:.0f}/100')} ({esc(label)})")

            if cond_lines:
                parts.append("  " + " | ".join(cond_lines))
            else:
                parts.append(unavailable("Market conditions"))
        except Exception as e:
            logger.warning(f"Market conditions failed: {e}")
            parts.append(unavailable("Market conditions"))

    # ── Run technicals and scoring ──────────────────────────────
    logger.info("Running technical analysis on daytrade universe...")
    scored_instruments = []
    all_ta = {}

    # Get all tickers to analyze
    from config.settings import get_all_yfinance_tickers
    all_tickers = get_all_yfinance_tickers()

    for t in all_tickers:
        yf_sym = t.get("yfinance")
        sym = t.get("symbol", yf_sym)
        if not yf_sym or sym not in prices:
            continue
        try:
            hist = builder.yf.get_history(yf_sym, period="3mo", interval="1d")
            if hist is not None and not hist.empty:
                ta = full_analysis(hist, ticker=sym)
                ta["name"] = t.get("name", yf_sym)
                ta["category"] = t.get("category", "other")
                all_ta[sym] = ta

                result = score_instrument(ta, prices[sym])
                if result:
                    scored_instruments.append(result)
        except Exception as e:
            logger.debug(f"Analysis failed for {yf_sym}: {e}")
            continue

    digest_data["all_ta"] = all_ta
    digest_data["prices"] = prices

    if not scored_instruments:
        parts.append(unavailable("Scoring data"))
        if out_data is not None:
            out_data.update(digest_data)
        return "\n".join(parts)

    # Sort and rank
    scored_instruments.sort(key=lambda x: x["score"], reverse=True)
    top_picks = scored_instruments[:10]
    honorable = scored_instruments[10:15]
    avoid_list = sorted(scored_instruments, key=lambda x: x["score"])[:5]

    # ── Multi-TF scoring for top picks ──────────────────────────
    logger.info("Computing multi-timeframe scores for top picks...")
    fundamentals_summary = {}
    for pick in top_picks:
        sym = pick["symbol"]
        try:
            # Find the matching ticker config for category
            cat = "us_stock"
            yf_sym = sym
            for t in all_tickers:
                if t.get("symbol") == sym or t.get("yfinance") == sym:
                    cat = t.get("category", "us_stock")
                    yf_sym = t.get("yfinance", sym)
                    break

            hist_2y = builder.yf.get_history(yf_sym, period="2y", interval="1d")
            if hist_2y is None or hist_2y.empty:
                continue

            # Swing (weekly)
            ta_w = weekly_full_analysis(hist_2y, ticker=sym)
            if not ta_w.get("error"):
                swing = score_instrument_swing(ta_w, prices[sym])
                if swing:
                    pick["swing_score"] = swing

            # Long-term (monthly)
            ta_m = monthly_full_analysis(hist_2y, ticker=sym)
            equity = is_equity_symbol(cat)
            fund_scores = None
            if equity:
                fund_data = fetch_fundamentals(sym, yf_sym)
                if fund_data:
                    fund_scores = score_fundamentals(fund_data)
                    fundamentals_summary[sym] = {
                        "metrics": fund_data.get("metrics", {}),
                        "scores": fund_scores,
                        "highlights": fund_data.get("highlights", {}),
                    }

            if not ta_m.get("error"):
                lt = score_instrument_longterm(ta_m, prices[sym], fundamentals=fund_scores, is_equity=equity)
                if lt:
                    pick["longterm_score"] = lt
        except Exception as e:
            logger.debug(f"Multi-TF scoring failed for {sym}: {e}")
            continue

    digest_data["top_picks"] = top_picks
    digest_data["honorable_mentions"] = honorable
    digest_data["avoid_list"] = avoid_list
    if fundamentals_summary:
        digest_data["fundamentals_summary"] = fundamentals_summary

    # ── Save retrace snapshot ────────────────────────────────────
    try:
        from src.retrace.snapshot import save_snapshot
        from src.retrace.scoring_config import load_scoring_weights
        from src.retrace.versioning import get_current_version_id
        save_snapshot(digest_data, load_scoring_weights(),
                      get_current_version_id("prompts") or "unversioned",
                      digest_type="daytrade")
    except Exception as e:
        logger.warning(f"Retrace snapshot save failed: {e}")

    # ── LLM Summary (full mode only) ───────────────────────────
    if analyzer and digest_data:
        try:
            summary = analyzer.analyze_section("daytrade_summary", digest_data, context=digest_data)
            if summary:
                parts.append(analysis_block(summary))
        except Exception as e:
            logger.warning(f"Daytrade LLM summary failed: {e}")

    # ── Top 10 Day Trade Picks ──────────────────────────────────
    if "top_picks" in enabled:
        parts.append(section_header("\U0001f3af TOP 10 DAY TRADE PICKS"))
        for i, pick in enumerate(top_picks, 1):
            track = None
            try:
                track = get_condensed_track_record(pick["symbol"])
            except Exception:
                pass
            parts.append(enhanced_pick_line(i, pick, track))

    # ── Multi-Timeframe Outlook (full mode) ─────────────────────
    if analyzer and digest_data.get("top_picks"):
        try:
            parts.append(section_header("\U0001f4d0 MULTI-TIMEFRAME OUTLOOK"))
            analysis = analyzer.analyze_section("multi_tf_outlook", digest_data, context=digest_data)
            if analysis:
                parts.append(analysis_block(analysis))
            else:
                parts.append(unavailable("Multi-timeframe outlook"))
        except Exception as e:
            logger.warning(f"Multi-TF outlook LLM failed: {e}")

    # ── Fundamentals Snapshot (full mode, equities only) ──────
    if analyzer and digest_data.get("fundamentals_summary"):
        try:
            parts.append(section_header("\U0001f4ca FUNDAMENTALS SNAPSHOT"))
            analysis = analyzer.analyze_section("fundamentals_analysis", digest_data, context=digest_data)
            if analysis:
                parts.append(analysis_block(analysis))
            else:
                parts.append(unavailable("Fundamentals snapshot"))
        except Exception as e:
            logger.warning(f"Fundamentals LLM failed: {e}")

    # ── Honorable Mentions ──────────────────────────────────────
    if "honorable_mentions" in enabled and honorable:
        parts.append(section_header("\U0001f4a1 HONORABLE MENTIONS"))
        for i, pick in enumerate(honorable, 11):
            trend_emoji = pick.get("trend_emoji", "")
            rsi_val = pick.get('rsi')
            rsi_str = f"{rsi_val:.0f}" if rsi_val is not None else "N/A"
            parts.append(
                f"  {i}. {esc(pick['symbol'])} — Score: {pick['score']:.0f} | "
                f"RSI {rsi_str} | ${pick['price']} | {trend_emoji}"
            )

    # ── Avoid List ──────────────────────────────────────────────
    if "avoid_list" in enabled and avoid_list:
        parts.append(section_header("\u26d4 AVOID TODAY"))
        for pick in avoid_list[:5]:
            reasons = []
            rsi = pick.get("rsi")
            if rsi and rsi > 70:
                reasons.append(f"RSI {rsi:.0f} (OB)")
            elif rsi and rsi < 30:
                reasons.append(f"RSI {rsi:.0f} (OS)")
            vol = pick.get("volume_ratio")
            if vol and vol < 0.8:
                reasons.append("low volume")
            trend = pick.get("trend", "")
            if trend in ("bearish", "weakly_bearish"):
                reasons.append(f"{trend.replace('_', ' ')} trend")
            reason_str = ", ".join(reasons) if reasons else f"score {pick['score']:.0f}"
            parts.append(f"  {esc(pick['symbol'])} — {esc(reason_str)}")

    # ── Custom Data Sources ─────────────────────────────────────
    try:
        custom_sources = builder.fetch_custom_sources("daytrade")
        for src_id, src_info in custom_sources.items():
            cfg = src_info["config"]
            integration = cfg.get("digest_integration", {})
            if integration.get("mode") == "section":
                title = integration.get("section_title", cfg.get("name", src_id))
                parts.append(section_header(f"\U0001f4cc {title}"))
                parts.append(custom_section_block(title, src_info["data"], cfg.get("type", "http")))
    except Exception as e:
        logger.warning(f"Custom sources failed: {e}")

    # ── Next Steps (full mode) ──────────────────────────────────
    if "next_steps" in enabled and analyzer and digest_data:
        parts.append(section_header("\U0001f3af NEXT STEPS"))
        try:
            next_steps = analyzer.analyze_section("next_steps_daytrade", digest_data, context=digest_data)
            if next_steps:
                parts.append(analysis_block(next_steps))
            else:
                parts.append(unavailable("Next steps"))
        except Exception as e:
            logger.warning(f"Next steps failed: {e}")
            parts.append(unavailable("Next steps"))

    # ── Footer ──────────────────────────────────────────────────
    parts.append(f"\n\n{esc(chr(9472) * 30)}\n{italic('Good luck & manage your risk!')}")

    if out_data is not None:
        out_data.update(digest_data)

    return "\n".join(parts)
