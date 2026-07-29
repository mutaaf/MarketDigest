"""Compass Ask — portfolio-aware conversational assistant.

Answers beginner questions using the user's own portfolio plus market data
already flowing through the app. Multi-turn: the client sends the running
conversation; history is folded into the prompt.
"""

import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

SYSTEM_PROMPT = """You are Compass, a friendly investing guide inside a family's portfolio app.
You help a beginner long-term investor understand their portfolio and options.

Rules:
- Plain English. Define any financial term the moment you use it.
- Ground answers in the PORTFOLIO and MARKET DATA provided — cite the actual numbers.
- Be honest about uncertainty. Never invent data that isn't provided.
- You are not a licensed financial advisor: frame guidance as education and things to
  consider, not directives. For big decisions, suggest they take their time.
- Keep answers short: 2-4 short paragraphs max, no bullet-point walls.
- Long-term, low-cost, diversified investing is your default philosophy.
- End every reply with one final line exactly like: TOPICS: concept one; concept two
  listing 1-3 core investing concepts from your answer worth studying later
  (e.g. "expense ratio", "diversification"). No other text on that line."""


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    portfolio: str | None = None
    messages: list[ChatMessage] = Field(min_length=1, max_length=30)


def _portfolio_context(slug: str | None) -> str:
    if not slug:
        return "The user has not selected a portfolio."
    try:
        from src.portfolio.analyzer import analyze_allocation
        from src.portfolio.health import assess_health
        from src.portfolio.store import load_portfolio
        from src.portfolio.valuation import value_portfolio

        portfolio = load_portfolio(slug)
        if portfolio is None:
            return "The user has not selected a portfolio."
        valuation = value_portfolio(portfolio)
        allocation = analyze_allocation(valuation)
        health = assess_health(allocation, valuation)

        lines = [f"PORTFOLIO '{portfolio['name']}':",
                 f"- Total value ${valuation['total_value']:,.0f} "
                 f"(cash ${valuation['cash']:,.0f}, day change {valuation['day_change_pct']:+.2f}%)"]
        for h in allocation.get("by_holding", []):
            lines.append(f"- {h['symbol']}: {h.get('shares')} shares, "
                         f"${h.get('value') or 0:,.0f} ({h.get('weight', 0):.1f}%), "
                         f"type={h.get('instrument_type')}")
        lines.append("Asset mix: " + ", ".join(
            f"{c['label']} {c['weight']:.0f}%" for c in allocation.get("asset_classes", [])))
        if health.get("grade"):
            lines.append(f"Health grade {health['grade']} ({health['score']}/100). "
                         + " ".join(f"{f['name']}: {f['detail']}" for f in health.get("factors", [])))
        if portfolio.get("targets"):
            lines.append(f"User's target mix: {portfolio['targets']}")
        return "\n".join(lines)
    except Exception:
        return "Portfolio data is temporarily unavailable — say so if asked about it."


def _symbol_context(text: str) -> str:
    """Attach data for tickers mentioned in the question (max 3 to bound latency)."""
    from config.settings import get_compass_universe

    universe = {u["symbol"]: u for u in get_compass_universe()}
    mentioned = []
    for word in re.findall(r"\b[A-Z]{2,6}\b", text):
        if word in universe and word not in mentioned:
            mentioned.append(word)
    if not mentioned:
        return ""

    blocks = []
    for sym in mentioned[:3]:
        meta = universe[sym]
        try:
            if meta["instrument_type"] == "etf":
                from src.analysis.etf_scorer import score_etf
                from src.fetchers.etf_data import fetch_etf_profile
                profile = fetch_etf_profile(sym, meta.get("yfinance", sym))
                if profile:
                    scored = score_etf(profile, meta.get("category"))
                    blocks.append(
                        f"{sym} ({profile.get('name')}): ETF, grade {scored['grade']}, "
                        f"expense ratio {profile.get('expense_ratio')}%, "
                        f"yield {profile.get('dividend_yield')}%, "
                        f"5y return {profile.get('return_5y')}%/yr, "
                        f"volatility {profile.get('volatility_1y')}%, "
                        f"risk {scored['risk_level']}")
            else:
                from src.analysis.daytrade_scorer import score_to_grade
                from src.analysis.fundamentals import fetch_fundamentals, score_fundamentals
                fnd = fetch_fundamentals(sym, meta.get("yfinance", sym))
                if fnd:
                    s = score_fundamentals(fnd)
                    m = fnd.get("metrics", {})
                    blocks.append(
                        f"{sym} ({meta.get('name')}): stock, sector {fnd.get('sector')}, "
                        f"quality grade {score_to_grade(s['composite'])} ({s['composite']}/100), "
                        f"P/E {m.get('pe_ratio')}, PEG {m.get('peg_ratio')}, "
                        f"revenue growth {m.get('revenue_growth')}%, "
                        f"dividend yield {m.get('dividend_yield')}%, "
                        f"price ${m.get('current_price')}, "
                        f"analyst avg target ${m.get('analyst_target')}")
        except Exception:
            blocks.append(f"{sym}: data temporarily unavailable.")
    return "MARKET DATA:\n" + "\n".join(blocks) if blocks else ""


@router.post("/chat")
async def chat(body: ChatRequest):
    from config.settings import get_settings
    from src.analysis.llm_providers import LLMProvider

    if not get_settings().has_llm_key():
        raise HTTPException(
            status_code=503,
            detail="The assistant needs an AI key to work. Add an Anthropic, OpenAI, or "
                   "Gemini key on the Settings page.",
        )

    question = body.messages[-1].content
    context_parts = [_portfolio_context(body.portfolio)]
    symbol_ctx = _symbol_context(question)
    if symbol_ctx:
        context_parts.append(symbol_ctx)

    history = ""
    if len(body.messages) > 1:
        turns = [f"{'User' if m.role == 'user' else 'Compass'}: {m.content}"
                 for m in body.messages[:-1][-8:]]
        history = "CONVERSATION SO FAR:\n" + "\n".join(turns) + "\n\n"

    user_prompt = f"{chr(10).join(context_parts)}\n\n{history}User's question: {question}"

    provider = LLMProvider()
    result = provider.generate(SYSTEM_PROMPT, user_prompt, max_tokens=700)
    if result is None:
        raise HTTPException(
            status_code=502,
            detail="The assistant couldn't reach any AI service right now. Try again in a minute.",
        )

    # Peel off the trailing TOPICS line into structured suggestions for Learn
    reply = result.text.strip()
    topics: list[str] = []
    match = re.search(r"\n?TOPICS:\s*(.+)\s*$", reply)
    if match:
        topics = [t.strip().rstrip(".") for t in re.split(r"[;,]", match.group(1))
                  if t.strip() and len(t.strip()) <= 40][:3]
        reply = reply[:match.start()].rstrip()
    return {"reply": reply, "provider": result.provider, "suggested_topics": topics}
