"""Market analysis orchestrator — builds prompts per section, calls LLM."""

import math
from pathlib import Path

import yaml

from src.analysis.llm_providers import LLMProvider
from src.utils.logging_config import get_logger

logger = get_logger("llm_analyzer")

PROMPTS_YAML = Path(__file__).parent.parent.parent / "config" / "prompts.yaml"

# ── Hardcoded defaults (fallback if YAML missing/incomplete) ────────

_DEFAULT_SYSTEM_PROMPT = (
    "You are a global financial market analyst writing a daily digest for readers who are NOT professional "
    "investors. Your job is to make markets understandable and actionable.\n\n"
    "Rules:\n"
    "- Explain what each number means and why it matters in plain language\n"
    "- Define financial terms briefly when you first use them (e.g. \"RSI (a momentum gauge from 0-100)\")\n"
    "- Connect moves across regions: how did Asia affect Europe? How does the dollar affect commodities?\n"
    "- Identify catalysts: central bank policy shifts, geopolitical events, economic data surprises\n"
    "- Explain cross-asset causality: why a strong dollar pressures gold, how bond yields affect equities\n"
    "- Be specific — reference the actual numbers from the data\n"
    "- Keep each section to 4-6 clear sentences\n"
    "- Write in flowing prose, no bullet points or headers\n"
    "- Do NOT use emojis or markdown formatting\n"
    "- End each section with one sentence on what to watch next"
)

DEFAULT_MAX_TOKENS = 500

_DEFAULT_PROMPTS = {
    "overnight": "Explain what happened in Asian and early-European trading sessions overnight. What catalysts drove the moves — central bank commentary, economic data releases, or geopolitical developments? How might these moves set the tone for European and US markets today?",
    "futures": "Explain what US futures are signaling ahead of the market open. Are futures confirming or diverging from overnight price action? What catalysts (earnings, economic data, geopolitics) could shift the direction at the open?",
    "forex": "Explain what's happening across the major currency pairs and what's driving dollar strength or weakness. Connect moves to interest rate differentials, central bank policy expectations, and risk appetite. How do these forex moves affect commodity prices and emerging market sentiment?",
    "commodities": "Explain the moves in commodities today considering dollar direction, geopolitical factors, and supply/demand dynamics. How do gold and oil relate to current risk sentiment and inflation expectations? What do agricultural commodity moves signal about global supply chains?",
    "crypto": "Analyze the cryptocurrency moves in the context of broader risk appetite and dollar strength. How does BTC correlate with equity futures today — is it trading as a risk asset or safe haven? What's driving altcoin performance relative to BTC, and are there any protocol-specific catalysts?",
    "calendar": "Summarize the key economic events and their potential market impact. Which release matters most for central bank policy and why? How might surprises in these numbers shift rate expectations and risk appetite?",
    "sentiment": "Explain what this sentiment reading means in plain terms and what's driving the mood. How does current sentiment compare to recent history — are we at extremes that suggest a reversal? What would need to happen to shift sentiment meaningfully from here?",
    "indices_close": "Summarize how US stock indices performed today and what drove the session. Was it sector rotation, macro data surprises, earnings, or global spillover? How did intraday price action evolve — was the close near the highs or lows of the day?",
    "sentiment_shift": "Explain how market sentiment evolved from the morning open to the close. What specific catalysts caused the shift during the trading session? Does the closing sentiment suggest continuation or reversal for tomorrow's open?",
    "movers": "Explain why these instruments moved the most today — identify the specific catalysts. What common themes connect the biggest winners and losers (risk-on/off, sector trends, earnings)? Do these moves suggest a broader market theme or are they idiosyncratic?",
    "week_review": "Provide a narrative summary of the trading week highlighting dominant themes and catalysts. How did central bank policy, economic data, and geopolitical events shape price action? How did events in one region or asset class ripple across to others? What's the key takeaway?",
    "rankings": "Explain the performance rankings for the week and what patterns stand out. Why did the top and bottom performers diverge — was it macro-driven or instrument-specific? What do these rankings tell us about the current market regime (risk-on, defensive, rotational)?",
    "sectors": "Explain the sector performance and what's driving the rotation. Which sectors led and lagged, and what does that say about economic growth expectations? How does sector rotation connect to interest rate expectations and risk appetite?",
    "economic": "Summarize the week's economic data releases and what they signal about the economy. Were there any surprises relative to expectations, and how did markets react? How might these data points influence central bank policy at the next meeting?",
    "technicals": "Summarize the technical picture across major instruments. Are there overbought or oversold extremes that historically precede reversals? What key support and resistance levels should readers watch in the week ahead?",
    "next_steps_morning": "Based on all the data above, provide 3-5 actionable items for TODAY. For each item: name the specific instrument or asset class, cite a key price level or threshold, and describe the scenario (e.g. 'if X breaks above Y, watch for Z'). Focus on what readers should monitor during today's trading session. Number each item. Write concisely — one sentence per item, no preamble.",
    "next_steps_afternoon": "Based on today's full session data above, provide 3-5 actionable items for positioning TOMORROW. For each item: explain how today's close sets up tomorrow — continuation or reversal scenarios, key levels to watch at tomorrow's open, and which catalysts could drive the next move. Number each item. Write concisely — one sentence per item, no preamble.",
    "next_steps_weekly": "Based on this week's full data above, provide 3-5 key themes for NEXT WEEK. For each theme: identify the catalyst (economic release, central bank event, earnings), the instruments most affected, and what would confirm or invalidate the theme. Number each item. Write concisely — one sentence per item, no preamble.",
    "quick_take": "Output ONLY 3-5 market insights, one per line. Each line MUST start with one of these prefixes: Bullish:, Bearish:, Event:, Data:, or Earnings:. One sentence per line, reference specific numbers. No preamble, no numbering, no closing remarks. Focus on what matters most to a general investor right now.",
    "events": "Summarize the economic events and earnings data provided. Highlight the most market-moving releases and connect them to Fed policy expectations, risk appetite, and sector implications. If earnings data is present, note any bellwether surprises. Keep it to 4-6 clear sentences in flowing prose.",
    "action_items_summary": "Based on all the market data above, write a 2-3 sentence executive summary highlighting the most important thing a general investor should know right now. Focus on the single biggest risk or opportunity, the key level to watch, and whether the overall setup is risk-on or risk-off. No bullet points, no headers, no emojis — just concise prose.",
    "daytrade_summary": "Based on the scored day trade picks and market conditions data above, write a 2-3 sentence pre-open thesis for today's day trading session. Identify the dominant theme (momentum, mean-reversion, sector rotation), highlight the best setup among the top picks with specific price levels, and note the key risk (VIX level, gap risk, low volume). Write concisely — no bullet points, no headers, no emojis.",
    "next_steps_daytrade": "Based on the day trade picks data above, provide 3-5 actionable trading items for TODAY's session. For each item: name the specific instrument, cite entry/target/stop levels, and describe the setup (e.g. 'NVDA breaking R1 at $125 with 1.8x volume — target $128, stop $123'). Focus on the highest-conviction setups from the scored picks. Number each item. Write concisely — one sentence per item, no preamble.",
    "multi_tf_outlook": "Based on the multi-timeframe technical data above (daily, weekly, monthly indicators), provide a concise outlook per timeframe. Day Trade: intraday setup and key levels. Swing (1-2 weeks): weekly trend direction and inflection points. Long Term (1-3 months): monthly trend health and value. Connect the timeframes — does weekly confirm or conflict with the daily? 2-3 sentences per timeframe, reference specific levels.",
    "fundamentals_analysis": "Based on the financial data above (income, balance sheet, cash flow, ratios), provide a concise fundamental assessment. Cover: Valuation — cheap or expensive vs earnings/assets? Quality — margins healthy and improving? Growth — revenue/EPS trending up? Health — debt manageable, cash flow positive? End with one sentence on whether fundamentals support the technical setup. Flowing prose, no bullets. Reference specific numbers.",
}

_DEFAULT_TOKEN_OVERRIDES = {
    "week_review": 700,
    "quick_take": 400,
    "events": 500,
    "action_items_summary": 200,
}

# ── YAML prompt config loading ─────────────────────────────────────

_prompt_config: dict | None = None


def _load_prompt_config() -> dict:
    global _prompt_config
    if _prompt_config is not None:
        return _prompt_config
    try:
        if PROMPTS_YAML.exists():
            with open(PROMPTS_YAML) as f:
                _prompt_config = yaml.safe_load(f) or {}
        else:
            _prompt_config = {}
    except Exception as e:
        logger.warning(f"Failed to load prompts.yaml: {e}")
        _prompt_config = {}
    return _prompt_config


def reload_prompts() -> None:
    """Clear cached prompt config, forcing re-read from YAML."""
    global _prompt_config
    _prompt_config = None


def _get_system_prompt() -> str:
    config = _load_prompt_config()
    return config.get("system_prompt", _DEFAULT_SYSTEM_PROMPT).strip()


def _get_user_prompt(section: str) -> str:
    config = _load_prompt_config()
    sections = config.get("sections", {})
    section_config = sections.get(section, {})
    return section_config.get("prompt", _DEFAULT_PROMPTS.get(section, "")).strip()


def _get_max_tokens(section: str) -> int:
    config = _load_prompt_config()
    sections = config.get("sections", {})
    section_config = sections.get(section, {})
    if "max_tokens" in section_config:
        return section_config["max_tokens"]
    default = config.get("default_max_tokens", DEFAULT_MAX_TOKENS)
    return _DEFAULT_TOKEN_OVERRIDES.get(section, default)


def _should_include_cross_context(section: str) -> bool:
    config = _load_prompt_config()
    sections = config.get("sections", {})
    section_config = sections.get(section, {})
    return section_config.get("include_cross_context", True)


# ── Data formatting helpers ─────────────────────────────────────


def _safe_num(value, default=0):
    """Return value if it's a valid number, else default."""
    if value is None:
        return default
    try:
        f = float(value)
        return default if math.isnan(f) or math.isinf(f) else value
    except (TypeError, ValueError):
        return default


def _format_price_data(data: dict) -> str:
    lines = []
    for sym, info in data.items():
        if isinstance(info, dict):
            name = info.get("name", sym)
            price = info.get("price")
            change = info.get("change_pct")
            if price is None:
                continue
            try:
                pf = float(price)
                if math.isnan(pf) or math.isinf(pf):
                    continue
            except (TypeError, ValueError):
                continue
            chg_str = ""
            if change is not None:
                try:
                    cf = float(change)
                    if not (math.isnan(cf) or math.isinf(cf)):
                        chg_str = f" ({cf:+.2f}%)"
                except (TypeError, ValueError):
                    pass
            lines.append(f"{name}: {pf:.5g}{chg_str}")
        else:
            lines.append(f"{sym}: {info}")
    return "\n".join(lines)


def _format_events(events: list) -> str:
    lines = []
    for e in events:
        parts = [e.get("event", "Unknown")]
        if e.get("actual") is not None:
            parts.append(f"Actual: {e['actual']}")
        if e.get("estimate") is not None:
            parts.append(f"Est: {e['estimate']}")
        if e.get("prev") is not None:
            parts.append(f"Prev: {e['prev']}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def _format_sentiment(data: dict) -> str:
    lines = [f"Composite Score: {_safe_num(data.get('composite_score'), 'N/A')}/100 — {data.get('classification', 'N/A')}"]
    for name, comp in data.get("components", {}).items():
        if comp.get("weight", 0) > 0:
            lines.append(f"  {name.upper()}: {_safe_num(comp.get('score'), 'N/A')} — {comp.get('label', '')}")
    return "\n".join(lines)


def _format_movers(movers: dict) -> str:
    lines = []
    for g in movers.get("gainers", []):
        lines.append(f"GAINER: {g.get('name', '?')} ({_safe_num(g.get('change_pct'), 0):+.2f}%)")
    for loser in movers.get("losers", []):
        lines.append(f"LOSER: {loser.get('name', '?')} ({_safe_num(loser.get('change_pct'), 0):+.2f}%)")
    return "\n".join(lines)


def _format_technicals(data: dict) -> str:
    lines = []
    for sym, ta in data.items():
        name = ta.get("name", sym)
        rsi = ta.get("rsi")
        trend = ta.get("trend", "N/A")
        rsi_str = f"RSI: {rsi:.0f}" if rsi else "RSI: N/A"
        lines.append(f"{name}: {rsi_str}, Trend: {trend}")
    return "\n".join(lines)


def _format_sectors(sectors: list) -> str:
    lines = []
    for s in sectors:
        sector_name = s["sector"].replace("_", " ").title()
        lines.append(
            f"{sector_name}: avg {s['avg_change_pct']:+.2f}% | "
            f"Best: {s['best']['name']} ({s['best']['change_pct']:+.2f}%) | "
            f"Worst: {s['worst']['name']} ({s['worst']['change_pct']:+.2f}%)"
        )
    return "\n".join(lines)


def _format_rankings(ranked: list) -> str:
    lines = []
    for i, inst in enumerate(ranked[:15], 1):
        name = inst.get("name", inst.get("symbol", "?"))
        chg = inst.get("change_pct", 0)
        price = inst.get("price", 0)
        lines.append(f"{i}. {name}: {price:.2f} ({chg:+.2f}%)")
    return "\n".join(lines)


def _format_economic(econ: dict, spread: dict | None = None) -> str:
    lines = []
    for series_id, data in econ.items():
        name = data.get("name", series_id)
        value = data.get("value", 0)
        prev = data.get("prev_value", 0)
        lines.append(f"{name}: {value:.2f} (prev: {prev:.2f})")
    if spread:
        inv = " INVERTED" if spread.get("inverted") else ""
        lines.append(f"10Y-2Y Spread: {spread['spread']:.2f}%{inv}")
    return "\n".join(lines)


def _format_comprehensive_events(data: dict) -> str:
    """Format comprehensive events data (economic + earnings + forward calendar) for LLM."""
    lines = []

    econ = data.get("economic_events", [])
    if econ:
        lines.append("ECONOMIC EVENTS:")
        for e in econ:
            parts = [e.get("event", "Unknown")]
            if e.get("actual") is not None:
                parts.append(f"Actual: {e['actual']}")
            if e.get("estimate") is not None:
                parts.append(f"Est: {e['estimate']}")
            if e.get("prev") is not None:
                parts.append(f"Prev: {e['prev']}")
            date_str = e.get("date", "")
            if date_str:
                parts.insert(0, date_str)
            lines.append("  " + " | ".join(parts))

    bellwether = data.get("earnings_bellwether", [])
    if bellwether:
        lines.append("\nBELLWETHER EARNINGS:")
        for e in bellwether:
            parts = [e.get("symbol", "?")]
            if e.get("eps_actual") is not None:
                parts.append(f"EPS Actual: {e['eps_actual']}")
            if e.get("eps_estimate") is not None:
                parts.append(f"EPS Est: {e['eps_estimate']}")
            if e.get("date"):
                parts.append(f"Date: {e['date']}")
            lines.append("  " + " | ".join(parts))

    other_count = data.get("earnings_other_count", 0)
    total = data.get("earnings_total", 0)
    if total > 0:
        lines.append(f"\nTotal earnings reporting: {total} ({len(bellwether)} bellwether, {other_count} others)")

    forward = data.get("forward_calendar", [])
    if forward:
        lines.append("\nFORWARD CALENDAR:")
        for item in forward:
            lines.append(f"  {item.get('event', '')}: {item.get('formatted', '')}")

    return "\n".join(lines)


def _format_multi_tf_data(data: dict) -> str:
    """Format multi-timeframe scores and targets for LLM context."""
    lines = []

    # Top picks with multi-TF scores
    top_picks = data.get("top_picks", [])
    if top_picks:
        lines.append("MULTI-TIMEFRAME SCORES FOR TOP PICKS:")
        for pick in top_picks:
            sym = pick.get("symbol", "?")
            dt_score = pick.get("score", 0)
            dt_grade = pick.get("grade", "?")
            line = f"  {sym}: DayTrade {dt_grade} ({dt_score:.0f}/100)"

            swing = pick.get("swing_score")
            if swing:
                line += f" | Swing {swing.get('grade', '?')} ({swing.get('score', 0):.0f}/100)"

            lt = pick.get("longterm_score")
            if lt:
                line += f" | LongTerm {lt.get('grade', '?')} ({lt.get('score', 0):.0f}/100)"

            lines.append(line)

            # Add signals per timeframe
            if swing and swing.get("signals"):
                lines.append(f"    Swing signals: {', '.join(swing['signals'])}")
            if lt and lt.get("signals"):
                lines.append(f"    LT signals: {', '.join(lt['signals'])}")

    return "\n".join(lines)


def _format_fundamentals_data(data: dict) -> str:
    """Format fundamentals data for LLM context."""
    lines = []
    fundamentals = data.get("fundamentals_summary", {})

    for sym, fund in fundamentals.items():
        lines.append(f"\n{sym} FUNDAMENTALS:")
        metrics = fund.get("metrics", {})
        scores = fund.get("scores", {})

        if scores:
            lines.append(f"  Scores: Valuation={scores.get('valuation', 'N/A')} | "
                         f"Profitability={scores.get('profitability', 'N/A')} | "
                         f"Growth={scores.get('growth', 'N/A')} | "
                         f"Health={scores.get('health', 'N/A')} | "
                         f"Composite={scores.get('composite', 'N/A')}")

        # Key ratios
        ratio_parts = []
        if metrics.get("pe_ratio") is not None:
            ratio_parts.append(f"P/E={metrics['pe_ratio']:.1f}")
        if metrics.get("pb_ratio") is not None:
            ratio_parts.append(f"P/B={metrics['pb_ratio']:.1f}")
        if metrics.get("ev_ebitda") is not None:
            ratio_parts.append(f"EV/EBITDA={metrics['ev_ebitda']:.1f}")
        if metrics.get("debt_equity") is not None:
            ratio_parts.append(f"D/E={metrics['debt_equity']:.2f}")
        if ratio_parts:
            lines.append(f"  Ratios: {' | '.join(ratio_parts)}")

        # Margins
        margin_parts = []
        if metrics.get("gross_margin") is not None:
            margin_parts.append(f"Gross={metrics['gross_margin']:.1f}%")
        if metrics.get("operating_margin") is not None:
            margin_parts.append(f"Op={metrics['operating_margin']:.1f}%")
        if metrics.get("net_margin") is not None:
            margin_parts.append(f"Net={metrics['net_margin']:.1f}%")
        if margin_parts:
            lines.append(f"  Margins: {' | '.join(margin_parts)}")

        # Growth
        growth_parts = []
        if metrics.get("revenue_growth") is not None:
            growth_parts.append(f"Rev={metrics['revenue_growth']:.1f}%")
        if metrics.get("eps_growth") is not None:
            growth_parts.append(f"EPS={metrics['eps_growth']:.1f}%")
        if metrics.get("roe") is not None:
            growth_parts.append(f"ROE={metrics['roe']:.1f}%")
        if growth_parts:
            lines.append(f"  Growth/Returns: {' | '.join(growth_parts)}")

        # Highlights
        highlights = fund.get("highlights", {})
        income = highlights.get("income", {})
        if income.get("revenue"):
            lines.append(f"  Revenue: ${income['revenue']:,.0f}")
        if income.get("eps"):
            lines.append(f"  EPS: ${income['eps']:.2f}")

        balance = highlights.get("balance", {})
        if balance.get("total_debt") and balance.get("cash"):
            lines.append(f"  Debt: ${balance['total_debt']:,.0f} | Cash: ${balance['cash']:,.0f}")

        cashflow = highlights.get("cashflow", {})
        if cashflow.get("fcf"):
            lines.append(f"  Free Cash Flow: ${cashflow['fcf']:,.0f}")

    return "\n".join(lines)


def _format_daytrade_picks(data: dict) -> str:
    lines = []
    # Market conditions
    sentiment = data.get("sentiment", {})
    if sentiment:
        score = _safe_num(sentiment.get("composite_score"), "N/A")
        label = sentiment.get("classification", "")
        lines.append(f"Sentiment: {score}/100 ({label})")

    # Top picks
    top_picks = data.get("top_picks", [])
    if top_picks:
        lines.append("\nTOP PICKS:")
        for i, pick in enumerate(top_picks, 1):
            signals = ", ".join(pick.get("signals", []))
            lines.append(
                f"  {i}. {pick['symbol']} ({pick.get('name', '')}) — Score: {pick['score']:.0f}/100 | "
                f"${pick.get('price', 0)} | RSI {pick.get('rsi', 'N/A')} | {pick.get('trend', '')} | "
                f"Entry: ${pick.get('entry', 0):.2f} Target: ${pick.get('target', 0):.2f} Stop: ${pick.get('stop', 0):.2f} | "
                f"R:R {pick.get('risk_reward', 0):.1f} | {signals}"
            )

    avoid = data.get("avoid_list", [])
    if avoid:
        lines.append("\nAVOID:")
        for pick in avoid[:5]:
            lines.append(f"  {pick['symbol']} — Score: {pick['score']:.0f} | RSI {pick.get('rsi', 'N/A')} | {pick.get('trend', '')}")

    return "\n".join(lines)


def _build_cross_context(ctx: dict) -> str:
    if not ctx:
        return ""

    parts = []

    forex = ctx.get("forex", {})
    dxy = forex.get("DXY", {}) if isinstance(forex, dict) else {}
    if dxy and dxy.get("price"):
        parts.append(f"DXY: {_safe_num(dxy.get('price'))} ({_safe_num(dxy.get('change_pct')):+.2f}%)")

    sentiment = ctx.get("sentiment", {})
    if isinstance(sentiment, dict) and sentiment.get("composite_score"):
        parts.append(f"Sentiment: {_safe_num(sentiment.get('composite_score'))}/100 ({sentiment.get('classification', 'N/A')})")

    futures = ctx.get("futures", {})
    if isinstance(futures, dict):
        for sym, info in list(futures.items())[:3]:
            if isinstance(info, dict) and info.get("price"):
                parts.append(f"{info.get('name', sym)}: {_safe_num(info.get('change_pct')):+.2f}%")

    commodities = ctx.get("commodities", {})
    if isinstance(commodities, dict):
        for key in ["GC=F", "CL=F"]:
            c = commodities.get(key, {})
            if isinstance(c, dict) and c.get("price"):
                parts.append(f"{c.get('name', key)}: {_safe_num(c.get('change_pct')):+.2f}%")

    if not parts:
        return ""
    return "\n\n=== CROSS-ASSET CONTEXT ===\n" + "\n".join(parts)


def _format_digest_summary(all_data: dict) -> str:
    parts = []
    for section_key in ["overnight", "futures", "forex", "commodities", "crypto",
                        "indices_close", "sentiment", "sentiment_shift",
                        "movers", "calendar", "events", "week_review", "rankings",
                        "sectors", "economic", "technicals"]:
        data = all_data.get(section_key)
        if data is None:
            continue

        label = section_key.upper().replace("_", " ")
        if isinstance(data, dict):
            if data.get("composite_score") is not None:
                parts.append(f"[{label}] {_format_sentiment(data)}")
            elif data.get("econ"):
                parts.append(f"[{label}] {_format_economic(data.get('econ', {}), data.get('spread'))}")
            elif data.get("gainers") or data.get("losers"):
                parts.append(f"[{label}] {_format_movers(data)}")
            elif data.get("economic_events") is not None or data.get("earnings_bellwether") is not None:
                parts.append(f"[{label}] {_format_comprehensive_events(data)}")
            else:
                parts.append(f"[{label}] {_format_price_data(data)}")
        elif isinstance(data, list):
            if data and isinstance(data[0], dict) and data[0].get("event"):
                parts.append(f"[{label}] {_format_events(data)}")
            elif data and isinstance(data[0], dict) and data[0].get("change_pct") is not None:
                parts.append(f"[{label}] {_format_rankings(data)}")

    return "\n\n".join(parts)


# ── Data header builders per section ────────────────────────────

_DATA_HEADERS = {
    "overnight": lambda data, ctx: f"=== OVERNIGHT RECAP ===\n{_format_price_data(data)}",
    "futures": lambda data, ctx: f"=== US FUTURES PRE-MARKET ===\n{_format_price_data(data)}",
    "forex": lambda data, ctx: f"=== FOREX MAJORS ===\n{_format_price_data(data)}",
    "commodities": lambda data, ctx: f"=== COMMODITIES ===\n{_format_price_data(data)}",
    "crypto": lambda data, ctx: f"=== CRYPTOCURRENCY ===\n{_format_price_data(data)}",
    "calendar": lambda data, ctx: f"=== ECONOMIC CALENDAR ===\n{_format_events(data)}",
    "sentiment": lambda data, ctx: f"=== MARKET SENTIMENT ===\n{_format_sentiment(data)}",
    "indices_close": lambda data, ctx: f"=== US INDICES CLOSING ===\n{_format_price_data(data)}",
    "sentiment_shift": lambda data, ctx: f"=== SENTIMENT SHIFT ===\n{_format_sentiment(data)}",
    "movers": lambda data, ctx: f"=== KEY MOVERS ===\n{_format_movers(data)}",
    "week_review": lambda data, ctx: f"=== WEEK IN REVIEW ===\n{_format_price_data(data)}",
    "rankings": lambda data, ctx: f"=== WEEKLY PERFORMANCE RANKINGS ===\n{_format_rankings(data)}",
    "sectors": lambda data, ctx: f"=== SECTOR COMPARISON ===\n{_format_sectors(data)}",
    "economic": lambda data, ctx: f"=== ECONOMIC DATA RECAP ===\n{_format_economic(data.get('econ', {}), data.get('spread'))}",
    "technicals": lambda data, ctx: f"=== TECHNICAL OUTLOOK ===\n{_format_technicals(data)}",
    "next_steps_morning": lambda data, ctx: f"=== FULL MORNING DIGEST DATA ===\n{_format_digest_summary(data)}",
    "next_steps_afternoon": lambda data, ctx: f"=== FULL AFTERNOON DIGEST DATA ===\n{_format_digest_summary(data)}",
    "next_steps_weekly": lambda data, ctx: f"=== FULL WEEKLY DIGEST DATA ===\n{_format_digest_summary(data)}",
    "quick_take": lambda data, ctx: f"=== ALL MARKET DATA ===\n{_format_digest_summary(data)}",
    "events": lambda data, ctx: f"=== COMPREHENSIVE EVENTS ===\n{_format_comprehensive_events(data)}",
    "action_items_summary": lambda data, ctx: f"=== ALL MARKET DATA FOR ACTION ITEMS ===\n{_format_digest_summary(data)}",
    "daytrade_summary": lambda data, ctx: f"=== DAY TRADE PICKS DATA ===\n{_format_daytrade_picks(data)}",
    "next_steps_daytrade": lambda data, ctx: f"=== DAY TRADE PICKS DATA ===\n{_format_daytrade_picks(data)}",
    "multi_tf_outlook": lambda data, ctx: f"=== MULTI-TIMEFRAME OUTLOOK ===\n{_format_multi_tf_data(data)}",
    "fundamentals_analysis": lambda data, ctx: f"=== FUNDAMENTALS DATA ===\n{_format_fundamentals_data(data)}",
}


def _build_user_prompt(section_name: str, data, context: dict) -> str:
    """Build the full user prompt: data header + user prompt text + optional cross-context."""
    header_fn = _DATA_HEADERS.get(section_name)
    if not header_fn:
        return ""

    header = header_fn(data, context)
    prompt_text = _get_user_prompt(section_name)
    cross_ctx = _build_cross_context(context) if _should_include_cross_context(section_name) else ""

    return f"{header}\n\n{prompt_text}{cross_ctx}"


class MarketAnalyzer:
    """Orchestrates LLM analysis for each digest section."""

    def __init__(self, provider: LLMProvider | None = None):
        self.provider = provider or LLMProvider()

    def analyze_section(self, section_name: str, data, context: dict | None = None) -> str | None:
        """Analyze a single section. Returns analysis text or None on failure."""
        if section_name not in _DATA_HEADERS:
            logger.warning(f"No prompt registered for section: {section_name}")
            return None

        try:
            user_prompt = _build_user_prompt(section_name, data, context or {})
        except Exception as e:
            logger.warning(f"Failed to build prompt for {section_name}: {e}")
            return None

        system_prompt = _get_system_prompt()
        max_tokens = _get_max_tokens(section_name)

        result = self.provider.generate(system_prompt, user_prompt, max_tokens=max_tokens)
        if result:
            logger.info(
                f"Section '{section_name}' analyzed by {result.provider}/{result.model} "
                f"({result.tokens_used} tokens, cached={result.cached})"
            )
            return result.text

        logger.warning(f"LLM analysis failed for section: {section_name}")
        return None

    def analyze_next_steps(self, digest_type: str, all_data: dict) -> str | None:
        section_name = f"next_steps_{digest_type}"
        return self.analyze_section(section_name, all_data, context=all_data)

    def generate_quick_take(self, all_data: dict) -> str | None:
        """Generate 3-5 quick take insight bullets from all available digest data."""
        return self.analyze_section("quick_take", all_data, context=all_data)

    def analyze_events(self, events_data: dict, context: dict | None = None) -> str | None:
        """Analyze comprehensive events (economic + earnings + forward calendar)."""
        return self.analyze_section("events", events_data, context=context)

    def analyze_action_items_summary(self, all_data: dict) -> str | None:
        """Generate a 2-3 sentence executive summary for the action items message."""
        return self.analyze_section("action_items_summary", all_data, context=all_data)

    def analyze_daytrade_summary(self, all_data: dict) -> str | None:
        """Generate a 2-3 sentence pre-open thesis for day trading."""
        return self.analyze_section("daytrade_summary", all_data, context=all_data)

    def analyze_full_digest(self, digest_type: str, all_data: dict) -> dict[str, str]:
        section_map = {
            "morning": ["overnight", "futures", "forex", "commodities", "crypto", "events", "calendar", "sentiment"],
            "afternoon": ["indices_close", "forex", "commodities", "crypto", "sentiment_shift", "movers", "events", "calendar"],
            "weekly": ["week_review", "rankings", "sectors", "crypto", "economic", "events", "technicals", "sentiment"],
        }

        sections = section_map.get(digest_type, [])
        results = {}

        for section in sections:
            data = all_data.get(section)
            if data is None:
                continue

            analysis = self.analyze_section(section, data, context=all_data)
            if analysis:
                results[section] = analysis

        return results
