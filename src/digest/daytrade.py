"""Day Trade Picks digest — pre-market ranked instrument picks."""

from src.digest.builder import DigestBuilder
from src.digest.formatter import (
    bold, code, esc, italic, section_header, analysis_block, unavailable,
)
from src.analysis.technicals import full_analysis, get_trend_emoji
from src.analysis.daytrade_scorer import score_instrument, rank_daytrade_picks
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

    digest_data["top_picks"] = top_picks
    digest_data["honorable_mentions"] = honorable
    digest_data["avoid_list"] = avoid_list

    # ── Save retrace snapshot ────────────────────────────────────
    try:
        from src.retrace.snapshot import save_snapshot
        from src.retrace.scoring_config import load_scoring_weights
        from src.retrace.versioning import get_current_version_id
        save_snapshot(digest_data, load_scoring_weights(),
                      get_current_version_id("prompts") or "unversioned")
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
    parts.append(section_header("\U0001f3af TOP 10 DAY TRADE PICKS"))
    for i, pick in enumerate(top_picks, 1):
        trend_emoji = pick.get("trend_emoji", "")
        trend = pick.get("trend", "neutral").replace("_", " ")
        vol_str = f"Vol {pick['volume_ratio']:.1f}x" if pick.get("volume_ratio") else ""

        # Color icon based on trend
        icon = "\U0001f7e2" if pick.get("trend") in ("bullish", "weakly_bullish") else "\U0001f534" if pick.get("trend") in ("bearish", "weakly_bearish") else "\u26aa"

        score_str = f"{pick['score']:.0f}/100"
        entry_str = f"${pick['entry']:.2f}"
        target_str = f"${pick['target']:.2f}"
        stop_str = f"${pick['stop']:.2f}"
        rsi_val = pick.get('rsi')
        rsi_str = f"{rsi_val:.0f}" if rsi_val is not None else "N/A"

        line = (
            f"  {i}. {icon} {bold(pick['symbol'])} — Score: {code(score_str)}\n"
            f"     ${pick['price']} | RSI {rsi_str} | {trend_emoji} {esc(trend)} | {esc(vol_str)}\n"
            f"     Entry: {code(entry_str)} | Target: {code(target_str)} | Stop: {code(stop_str)}"
        )
        if pick.get("signals"):
            line += f"\n     {esc(chr(8594))} {esc(', '.join(pick['signals']))}"
        parts.append(line)

    # ── Honorable Mentions ──────────────────────────────────────
    if honorable:
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
    if avoid_list:
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

    # ── Next Steps (full mode) ──────────────────────────────────
    if analyzer and digest_data:
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
