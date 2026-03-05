"""Options flow analysis engine — premium breakdown, conviction, Greeks, snapshots, LLM arc reading."""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path

from src.utils.logging_config import get_logger

logger = get_logger("options_flow")

PROJECT_ROOT = Path(__file__).parent.parent.parent
SNAPSHOT_DIR = PROJECT_ROOT / "logs" / "options_flow"


# ── Premium & Conviction ────────────────────────────────────────


def _compute_premium(contracts: list) -> float:
    """Estimated premium = sum(volume * midpoint) across contracts."""
    total = 0.0
    for c in contracts:
        vol = c.get("volume") or 0
        bid = c.get("bid") or 0.0
        ask = c.get("ask") or 0.0
        mid = (bid + ask) / 2
        total += vol * mid * 100  # each contract = 100 shares
    return round(total, 2)


def _compute_conviction(cp_ratio: float) -> tuple[str, int]:
    """Map C/P ratio to conviction label + 0-100 score."""
    if cp_ratio >= 3.0:
        return "Extreme Bull", 95
    if cp_ratio >= 2.0:
        return "Strong Bull", 80
    if cp_ratio >= 1.3:
        return "Bull", 65
    if cp_ratio >= 0.8:
        return "Neutral", 50
    if cp_ratio >= 0.5:
        return "Bear", 35
    if cp_ratio >= 0.3:
        return "Strong Bear", 20
    return "Extreme Bear", 5


# ── Max Pain ────────────────────────────────────────────────────


def _compute_max_pain(chains: dict, stock_price: float) -> float | None:
    """Strike that minimizes total OI-weighted loss for option writers."""
    # Collect all unique strikes and their OI
    strike_call_oi: dict[float, int] = {}
    strike_put_oi: dict[float, int] = {}

    for _exp, data in chains.items():
        for c in data.get("calls", []):
            s = c.get("strike")
            if s is not None:
                strike_call_oi[s] = strike_call_oi.get(s, 0) + (c.get("openInterest") or 0)
        for p in data.get("puts", []):
            s = p.get("strike")
            if s is not None:
                strike_put_oi[s] = strike_put_oi.get(s, 0) + (p.get("openInterest") or 0)

    all_strikes = sorted(set(strike_call_oi.keys()) | set(strike_put_oi.keys()))
    if not all_strikes:
        return None

    min_pain = float("inf")
    max_pain_strike = stock_price

    for test_strike in all_strikes:
        total_pain = 0.0
        # Call holders lose if stock < strike (ITM calls expire worthless above test_strike)
        for s, oi in strike_call_oi.items():
            if test_strike > s:
                total_pain += (test_strike - s) * oi * 100
        # Put holders lose if stock > strike
        for s, oi in strike_put_oi.items():
            if test_strike < s:
                total_pain += (s - test_strike) * oi * 100

        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = test_strike

    return round(max_pain_strike, 2)


# ── Black-Scholes Delta (no scipy) ─────────────────────────────


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _black_scholes_delta(S: float, K: float, T: float, r: float, sigma: float, opt_type: str) -> float:
    """Compute Black-Scholes delta. opt_type = 'call' or 'put'."""
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    if opt_type == "call":
        return _norm_cdf(d1)
    return _norm_cdf(d1) - 1.0


def _black_scholes_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Compute Black-Scholes gamma (same for calls and puts)."""
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return math.exp(-0.5 * d1 ** 2) / (S * sigma * math.sqrt(2 * math.pi * T))


# ── Greeks Summary ──────────────────────────────────────────────


def _compute_greeks_summary(chains: dict, stock_price: float) -> dict:
    """Net delta, total gamma, put wall, call wall from all chains."""
    r = 0.05  # risk-free rate
    net_delta = 0.0
    total_gamma = 0.0
    call_oi_by_strike: dict[float, int] = {}
    put_oi_by_strike: dict[float, int] = {}

    now = datetime.now()

    for exp_str, data in chains.items():
        try:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d")
        except ValueError:
            continue
        T = max((exp_date - now).days / 365.0, 1 / 365.0)

        for c in data.get("calls", []):
            strike = c.get("strike")
            oi = c.get("openInterest") or 0
            vol = c.get("volume") or 0
            iv = c.get("impliedVolatility") or 0.3
            if strike and oi > 0:
                delta = _black_scholes_delta(stock_price, strike, T, r, iv, "call")
                gamma = _black_scholes_gamma(stock_price, strike, T, r, iv)
                net_delta += delta * oi * 100
                total_gamma += gamma * oi * 100
                call_oi_by_strike[strike] = call_oi_by_strike.get(strike, 0) + oi

        for p in data.get("puts", []):
            strike = p.get("strike")
            oi = p.get("openInterest") or 0
            iv = p.get("impliedVolatility") or 0.3
            if strike and oi > 0:
                delta = _black_scholes_delta(stock_price, strike, T, r, iv, "put")
                gamma = _black_scholes_gamma(stock_price, strike, T, r, iv)
                net_delta += delta * oi * 100
                total_gamma += gamma * oi * 100
                put_oi_by_strike[strike] = put_oi_by_strike.get(strike, 0) + oi

    # Walls = strikes with highest OI
    call_wall = max(call_oi_by_strike, key=call_oi_by_strike.get) if call_oi_by_strike else None
    put_wall = max(put_oi_by_strike, key=put_oi_by_strike.get) if put_oi_by_strike else None

    max_pain = _compute_max_pain(chains, stock_price)

    return {
        "net_delta": round(net_delta, 0),
        "total_gamma": round(total_gamma, 0),
        "put_wall": put_wall,
        "call_wall": call_wall,
        "max_pain": max_pain,
    }


# ── Strike Heatmap ──────────────────────────────────────────────


def _build_strike_heatmap(chains: dict, top_n: int = 20) -> list[dict]:
    """Top strikes by total premium."""
    strike_data: dict[float, dict] = {}

    for _exp, data in chains.items():
        for c in data.get("calls", []):
            s = c.get("strike")
            if s is None:
                continue
            if s not in strike_data:
                strike_data[s] = {"strike": s, "call_premium": 0.0, "put_premium": 0.0, "call_oi": 0, "put_oi": 0}
            vol = c.get("volume") or 0
            mid = ((c.get("bid") or 0) + (c.get("ask") or 0)) / 2
            strike_data[s]["call_premium"] += vol * mid * 100
            strike_data[s]["call_oi"] += c.get("openInterest") or 0

        for p in data.get("puts", []):
            s = p.get("strike")
            if s is None:
                continue
            if s not in strike_data:
                strike_data[s] = {"strike": s, "call_premium": 0.0, "put_premium": 0.0, "call_oi": 0, "put_oi": 0}
            vol = p.get("volume") or 0
            mid = ((p.get("bid") or 0) + (p.get("ask") or 0)) / 2
            strike_data[s]["put_premium"] += vol * mid * 100
            strike_data[s]["put_oi"] += p.get("openInterest") or 0

    for d in strike_data.values():
        d["net_premium"] = round(d["call_premium"] - d["put_premium"], 2)
        d["call_premium"] = round(d["call_premium"], 2)
        d["put_premium"] = round(d["put_premium"], 2)

    sorted_strikes = sorted(strike_data.values(), key=lambda x: x["call_premium"] + x["put_premium"], reverse=True)
    return sorted_strikes[:top_n]


# ── Expiry Distribution ─────────────────────────────────────────


def _build_expiry_distribution(chains: dict) -> list[dict]:
    """Premium grouped by expiry date."""
    now = datetime.now()
    distribution = []
    total_all = 0.0

    for exp_str, data in chains.items():
        call_prem = _compute_premium(data.get("calls", []))
        put_prem = _compute_premium(data.get("puts", []))
        total = call_prem + put_prem
        total_all += total

        try:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d")
            days_to_expiry = max((exp_date - now).days, 0)
        except ValueError:
            days_to_expiry = 0

        # Top strike by volume for this expiry
        all_contracts = data.get("calls", []) + data.get("puts", [])
        top_strike = None
        if all_contracts:
            best = max(all_contracts, key=lambda c: c.get("volume") or 0)
            top_strike = best.get("strike")

        cp_ratio = round(call_prem / put_prem, 2) if put_prem > 0 else 99.99

        distribution.append({
            "expiry": exp_str,
            "days_to_expiry": days_to_expiry,
            "call_premium": call_prem,
            "put_premium": put_prem,
            "total_premium": total,
            "top_strike": top_strike,
            "cp_ratio": cp_ratio,
        })

    # Add pct_of_total
    for d in distribution:
        d["pct_of_total"] = round(d["total_premium"] / total_all * 100, 1) if total_all > 0 else 0.0

    distribution.sort(key=lambda x: x["total_premium"], reverse=True)
    return distribution


# ── OI Analysis ─────────────────────────────────────────────────


def _compute_oi_analysis(chains: dict) -> dict:
    """Total call/put OI, PCR by OI, put/call walls."""
    total_call_oi = 0
    total_put_oi = 0
    call_oi_by_strike: dict[float, int] = {}
    put_oi_by_strike: dict[float, int] = {}

    for _exp, data in chains.items():
        for c in data.get("calls", []):
            oi = c.get("openInterest") or 0
            total_call_oi += oi
            s = c.get("strike")
            if s is not None:
                call_oi_by_strike[s] = call_oi_by_strike.get(s, 0) + oi

        for p in data.get("puts", []):
            oi = p.get("openInterest") or 0
            total_put_oi += oi
            s = p.get("strike")
            if s is not None:
                put_oi_by_strike[s] = put_oi_by_strike.get(s, 0) + oi

    pcr_oi = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0.0
    put_wall = max(put_oi_by_strike, key=put_oi_by_strike.get) if put_oi_by_strike else None
    call_wall = max(call_oi_by_strike, key=call_oi_by_strike.get) if call_oi_by_strike else None

    return {
        "total_call_oi": total_call_oi,
        "total_put_oi": total_put_oi,
        "pcr_oi": pcr_oi,
        "put_wall": put_wall,
        "call_wall": call_wall,
    }


# ── Main Analysis ───────────────────────────────────────────────


def analyze_options_flow(chain_data: dict) -> dict:
    """Main entry point: produce full flow analysis from raw chain data."""
    symbol = chain_data["symbol"]
    stock_price = chain_data["stock_price"]
    chains = chain_data["chains"]

    # Aggregate premiums
    total_call_premium = 0.0
    total_put_premium = 0.0
    for _exp, data in chains.items():
        total_call_premium += _compute_premium(data.get("calls", []))
        total_put_premium += _compute_premium(data.get("puts", []))

    total_premium = total_call_premium + total_put_premium
    cp_ratio = round(total_call_premium / total_put_premium, 2) if total_put_premium > 0 else 99.99
    conviction, conviction_score = _compute_conviction(cp_ratio)

    # Top strikes by call/put premium
    call_strike_prem: dict[float, float] = {}
    put_strike_prem: dict[float, float] = {}
    for _exp, data in chains.items():
        for c in data.get("calls", []):
            s = c.get("strike")
            if s:
                vol = c.get("volume") or 0
                mid = ((c.get("bid") or 0) + (c.get("ask") or 0)) / 2
                call_strike_prem[s] = call_strike_prem.get(s, 0) + vol * mid * 100
        for p in data.get("puts", []):
            s = p.get("strike")
            if s:
                vol = p.get("volume") or 0
                mid = ((p.get("bid") or 0) + (p.get("ask") or 0)) / 2
                put_strike_prem[s] = put_strike_prem.get(s, 0) + vol * mid * 100

    top_call_strike = max(call_strike_prem, key=call_strike_prem.get) if call_strike_prem else None
    top_put_strike = max(put_strike_prem, key=put_strike_prem.get) if put_strike_prem else None

    return {
        "symbol": symbol,
        "stock_price": stock_price,
        "fetched_at": chain_data.get("fetched_at"),
        "total_call_premium": round(total_call_premium, 2),
        "total_put_premium": round(total_put_premium, 2),
        "total_premium": round(total_premium, 2),
        "cp_ratio": cp_ratio,
        "conviction": conviction,
        "conviction_score": conviction_score,
        "top_call_strike": top_call_strike,
        "top_put_strike": top_put_strike,
        "expiry_distribution": _build_expiry_distribution(chains),
        "strike_heatmap": _build_strike_heatmap(chains),
        "greeks_summary": _compute_greeks_summary(chains, stock_price),
        "oi_analysis": _compute_oi_analysis(chains),
    }


# ── Snapshot Persistence ────────────────────────────────────────


def save_flow_snapshot(symbol: str, flow_data: dict) -> None:
    """Save flow analysis to logs/options_flow/{SYMBOL}/YYYY-MM-DD.json."""
    today = datetime.now().strftime("%Y-%m-%d")
    sym_dir = SNAPSHOT_DIR / symbol.upper()
    sym_dir.mkdir(parents=True, exist_ok=True)
    path = sym_dir / f"{today}.json"
    try:
        with open(path, "w") as f:
            json.dump(flow_data, f, indent=2, default=str)
        logger.debug(f"Saved options flow snapshot: {path}")
    except Exception as e:
        logger.warning(f"Failed to save flow snapshot: {e}")


def load_flow_history(symbol: str, days: int = 5) -> list[dict]:
    """Load last N days of flow snapshots for a symbol."""
    sym_dir = SNAPSHOT_DIR / symbol.upper()
    if not sym_dir.exists():
        return []

    files = sorted(sym_dir.glob("*.json"), reverse=True)[:days]
    history = []
    for f in files:
        try:
            with open(f) as fh:
                data = json.load(fh)
                data["_date"] = f.stem  # YYYY-MM-DD
                history.append(data)
        except Exception as e:
            logger.warning(f"Failed to load snapshot {f}: {e}")
    return history


def build_daily_breakdown(history: list[dict]) -> list[dict]:
    """Transform history into daily flow cards with sentiment labels."""
    days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    breakdown = []

    for h in history:
        date_str = h.get("_date", "")
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            day_label = days_of_week[dt.weekday()]
        except ValueError:
            day_label = "?"

        cp = h.get("cp_ratio", 1.0)
        if cp >= 1.5:
            sentiment = "Bullish"
        elif cp >= 0.8:
            sentiment = "Neutral"
        else:
            sentiment = "Bearish"

        breakdown.append({
            "day": day_label,
            "date": date_str,
            "total_call_premium": h.get("total_call_premium", 0),
            "total_put_premium": h.get("total_put_premium", 0),
            "total_premium": h.get("total_premium", 0),
            "cp_ratio": cp,
            "sentiment": sentiment,
        })

    return breakdown


# ── Arc Status ──────────────────────────────────────────────────


def _compute_arc_status(history: list[dict]) -> str:
    """Determine arc status based on C/P ratio trend over recent days."""
    if len(history) < 2:
        return "Steady"
    ratios = [h.get("cp_ratio", 1.0) for h in history]
    # history is newest-first; reverse for chronological
    ratios = list(reversed(ratios))
    if len(ratios) >= 2:
        if ratios[-1] > ratios[0] * 1.15:
            return "Building"
        if ratios[-1] < ratios[0] * 0.85:
            return "Fading"
    return "Steady"


# ── LLM Arc Reading ────────────────────────────────────────────


def generate_arc_reading(flow_data: dict, history: list[dict]) -> str | None:
    """Generate LLM arc reading narrative from flow data."""
    try:
        from src.analysis.llm_providers import LLMProvider
    except Exception:
        return None

    provider = LLMProvider()
    arc_status = _compute_arc_status(history)

    # Load prompt from YAML
    prompt_text = (
        "Based on the options flow data (call/put premiums, C/P ratio trend, strike concentration, "
        "expiry distribution, OI walls, max pain), provide a conviction arc reading. Describe whether "
        "flow suggests building directional bets, hedging, or distribution. Reference specific C/P ratios, "
        "dominant strikes, and how flow evolved across sessions. Note if the arc is Building, Steady, or Fading. "
        "End with what to watch for confirmation/invalidation. 3-5 sentences, prose, no bullets."
    )
    try:
        from pathlib import Path
        import yaml
        prompts_yaml = Path(__file__).parent.parent.parent / "config" / "prompts.yaml"
        if prompts_yaml.exists():
            with open(prompts_yaml) as f:
                config = yaml.safe_load(f) or {}
            sections = config.get("sections", {})
            if "options_arc_reading" in sections:
                prompt_text = sections["options_arc_reading"].get("prompt", prompt_text)
    except Exception:
        pass

    system_prompt = (
        "You are an options flow analyst providing arc readings for traders. "
        "Write in direct prose. No emojis, no markdown, no bullet points."
    )

    # Build context
    context_parts = [
        f"Symbol: {flow_data.get('symbol')}",
        f"Stock Price: ${flow_data.get('stock_price')}",
        f"Total Call Premium: ${flow_data.get('total_call_premium', 0):,.0f}",
        f"Total Put Premium: ${flow_data.get('total_put_premium', 0):,.0f}",
        f"C/P Ratio: {flow_data.get('cp_ratio')}",
        f"Conviction: {flow_data.get('conviction')} ({flow_data.get('conviction_score')}/100)",
        f"Arc Status: {arc_status}",
    ]

    greeks = flow_data.get("greeks_summary", {})
    if greeks:
        context_parts.append(f"Max Pain: ${greeks.get('max_pain')}")
        context_parts.append(f"Put Wall: ${greeks.get('put_wall')}")
        context_parts.append(f"Call Wall: ${greeks.get('call_wall')}")
        context_parts.append(f"Net Delta: {greeks.get('net_delta')}")

    if flow_data.get("top_call_strike"):
        context_parts.append(f"Top Call Strike: ${flow_data['top_call_strike']}")
    if flow_data.get("top_put_strike"):
        context_parts.append(f"Top Put Strike: ${flow_data['top_put_strike']}")

    # Daily history
    if history:
        context_parts.append("\nDaily C/P Ratios (recent):")
        for h in history[:5]:
            context_parts.append(f"  {h.get('_date', '?')}: C/P={h.get('cp_ratio', '?')}, Premium=${h.get('total_premium', 0):,.0f}")

    user_prompt = "\n".join(context_parts) + "\n\n" + prompt_text

    result = provider.generate(system_prompt, user_prompt, max_tokens=400)
    return result.text if result else None


# ── Section-Level LLM Analyses ────────────────────────────────


def _load_section_prompts() -> dict[str, dict]:
    """Load options section prompts from YAML."""
    try:
        import yaml
        prompts_yaml = PROJECT_ROOT / "config" / "prompts.yaml"
        if prompts_yaml.exists():
            with open(prompts_yaml) as f:
                config = yaml.safe_load(f) or {}
            return config.get("sections", {})
    except Exception:
        pass
    return {}


def generate_section_analyses(
    flow_data: dict, history: list, news: list | None = None
) -> dict[str, str | None]:
    """Generate LLM analysis for each options section independently."""
    try:
        from src.analysis.llm_providers import LLMProvider
    except Exception:
        return {k: None for k in [
            "flow_summary", "premium_analysis", "greeks_analysis",
            "expiry_analysis", "strike_analysis", "news_correlation", "action_items",
        ]}

    provider = LLMProvider()
    sections_config = _load_section_prompts()
    arc_status = _compute_arc_status(history)

    system_prompt = (
        "You are an options flow analyst writing for traders. Explain clearly what the data means "
        "and why it matters. Write in direct prose. No emojis, no markdown, no bullet points "
        "(except for action items which should be numbered)."
    )

    # Common context header
    base_context = (
        f"Symbol: {flow_data.get('symbol')}\n"
        f"Stock Price: ${flow_data.get('stock_price')}\n"
        f"Conviction: {flow_data.get('conviction')} ({flow_data.get('conviction_score')}/100)\n"
        f"Arc Status: {arc_status}\n"
    )

    # Section definitions: key -> (yaml_key, context_builder, fallback_prompt, max_tokens)
    greeks = flow_data.get("greeks_summary", {})
    oi = flow_data.get("oi_analysis", {})

    section_defs = {
        "flow_summary": {
            "yaml_key": "options_flow_summary",
            "context": (
                base_context
                + f"Total Call Premium: ${flow_data.get('total_call_premium', 0):,.0f}\n"
                + f"Total Put Premium: ${flow_data.get('total_put_premium', 0):,.0f}\n"
                + f"C/P Ratio: {flow_data.get('cp_ratio')}\n"
                + f"Total Premium: ${flow_data.get('total_premium', 0):,.0f}\n"
            ),
            "max_tokens": 300,
        },
        "premium_analysis": {
            "yaml_key": "options_premium_analysis",
            "context": (
                base_context
                + f"Total Call Premium: ${flow_data.get('total_call_premium', 0):,.0f}\n"
                + f"Total Put Premium: ${flow_data.get('total_put_premium', 0):,.0f}\n"
                + f"C/P Ratio: {flow_data.get('cp_ratio')}\n"
                + f"Top Call Strike: ${flow_data.get('top_call_strike')}\n"
                + f"Top Put Strike: ${flow_data.get('top_put_strike')}\n"
            ),
            "max_tokens": 300,
        },
        "greeks_analysis": {
            "yaml_key": "options_greeks_analysis",
            "context": (
                base_context
                + f"Max Pain: ${greeks.get('max_pain')}\n"
                + f"Put Wall: ${greeks.get('put_wall')}\n"
                + f"Call Wall: ${greeks.get('call_wall')}\n"
                + f"Net Delta: {greeks.get('net_delta'):,.0f}\n"
                + f"Total Gamma: {greeks.get('total_gamma'):,.0f}\n"
                + f"Total Call OI: {oi.get('total_call_oi', 0):,}\n"
                + f"Total Put OI: {oi.get('total_put_oi', 0):,}\n"
                + f"Put/Call Ratio (OI): {oi.get('pcr_oi', 0)}\n"
            ),
            "max_tokens": 350,
        },
        "expiry_analysis": {
            "yaml_key": "options_expiry_analysis",
            "context": (
                base_context + "Expiry Distribution:\n"
                + "\n".join(
                    f"  {d['expiry']} ({d['days_to_expiry']}d): ${d['total_premium']:,.0f} ({d['pct_of_total']:.0f}%)"
                    for d in flow_data.get("expiry_distribution", [])[:8]
                )
                + "\n"
            ),
            "max_tokens": 300,
        },
        "strike_analysis": {
            "yaml_key": "options_strike_analysis",
            "context": (
                base_context + "Top Strikes by Premium:\n"
                + "\n".join(
                    f"  ${h['strike']}: Call=${h['call_premium']:,.0f} Put=${h['put_premium']:,.0f} Net=${h['net_premium']:,.0f}"
                    for h in flow_data.get("strike_heatmap", [])[:10]
                )
                + "\n"
            ),
            "max_tokens": 300,
        },
        "news_correlation": {
            "yaml_key": "options_news_correlation",
            "context": (
                base_context
                + f"C/P Ratio: {flow_data.get('cp_ratio')}\n"
                + f"Conviction: {flow_data.get('conviction')}\n"
                + "\nRecent News Headlines:\n"
                + (
                    "\n".join(f"  - {n.get('title', '')}" for n in (news or [])[:5])
                    if news else "  No news available\n"
                )
            ),
            "max_tokens": 350,
        },
        "action_items": {
            "yaml_key": "options_action_items",
            "context": (
                base_context
                + f"C/P Ratio: {flow_data.get('cp_ratio')}\n"
                + f"Max Pain: ${greeks.get('max_pain')}\n"
                + f"Put Wall: ${greeks.get('put_wall')}\n"
                + f"Call Wall: ${greeks.get('call_wall')}\n"
                + f"Net Delta: {greeks.get('net_delta'):,.0f}\n"
                + f"Top Call Strike: ${flow_data.get('top_call_strike')}\n"
                + f"Top Put Strike: ${flow_data.get('top_put_strike')}\n"
            ),
            "max_tokens": 400,
        },
    }

    results: dict[str, str | None] = {}

    for key, defn in section_defs.items():
        try:
            yaml_key = defn["yaml_key"]
            prompt_text = ""
            if yaml_key in sections_config:
                prompt_text = sections_config[yaml_key].get("prompt", "")
            if not prompt_text:
                prompt_text = f"Analyze the {key.replace('_', ' ')} based on the data above."

            user_prompt = defn["context"] + "\n" + prompt_text
            result = provider.generate(system_prompt, user_prompt, max_tokens=defn["max_tokens"])
            results[key] = result.text if result else None
        except Exception as e:
            logger.warning(f"Failed to generate {key}: {e}")
            results[key] = None

    return results
