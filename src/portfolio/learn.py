"""Learn knowledge map — topics the family collects as they use Compass.

Saved topics live per portfolio in data/learn/{slug}.json. Explanations are
LLM-written once at save time and stored, so recall is instant and offline.
"Teach me" generates audience-tailored versions (kid / adult) on demand and
caches them into the topic once generated.
"""

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
LEARN_DIR = PROJECT_ROOT / "data" / "learn"

_EXPLAIN_SYSTEM = """You write tiny investing explainers for a family app.
Respond with ONLY JSON, no fences: {"short": "...", "body": "..."}
- short: one catchy plain-English tagline, max 8 words
- body: 2-4 sentences a beginner instantly gets. Concrete numbers/examples
  beat abstractions. No jargon without an inline definition."""

_TEACH_SYSTEM = {
    "kid": """You explain money ideas to a curious 8-12 year old. Use a fun,
concrete analogy from their world (lemonade stands, allowances, video games,
trading cards). 3-5 short sentences, warm and playful, zero jargon. End with
one simple question they could think about or try with a parent.""",
    "adult": """You explain investing ideas to a smart adult beginner. Be
practical: what it is, why it matters for THEIR money, and one rule of thumb
they can actually use. 4-6 sentences, plain English, concrete numbers.""",
}


def _path(slug: str) -> Path:
    return LEARN_DIR / f"{slug}.json"


def _topic_id(term: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", term.strip().lower()).strip("-")[:60]


def get_topics(slug: str) -> list[dict]:
    try:
        return json.loads(_path(slug).read_text())
    except (OSError, json.JSONDecodeError):
        return []


def _save(slug: str, topics: list[dict]) -> None:
    LEARN_DIR.mkdir(parents=True, exist_ok=True)
    path = _path(slug)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(topics, f, indent=1)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def add_topic(slug: str, term: str, context: str = "") -> dict:
    """Save a topic, writing its explanation with the LLM. Returns the topic,
    or an {'error': ...} dict with a friendly message."""
    from config.settings import get_settings

    term = term.strip()
    tid = _topic_id(term)
    if not tid:
        return {"error": "That topic name didn't make sense."}
    topics = get_topics(slug)
    for t in topics:
        if t["id"] == tid:
            return t  # already saved — recall it

    short, body = "", ""
    if get_settings().has_llm_key():
        from src.analysis.llm_providers import LLMProvider
        prompt = f"Explain the investing concept: {term}"
        if context:
            prompt += f"\nIt came up in this context: {context[:500]}"
        result = LLMProvider().generate(_EXPLAIN_SYSTEM, prompt, max_tokens=300)
        if result:
            try:
                cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", result.text.strip(), flags=re.MULTILINE)
                data = json.loads(cleaned)
                short = str(data.get("short", ""))[:80]
                body = str(data.get("body", ""))[:1200]
            except (json.JSONDecodeError, AttributeError):
                body = result.text.strip()[:1200]
    if not body:
        body = "Saved — ask Compass to explain this and the answer will build your understanding."

    topic = {
        "id": tid, "term": term, "short": short, "body": body,
        "source": "ai", "added": datetime.now().isoformat(timespec="seconds"),
        "taught": {},
    }
    topics.insert(0, topic)
    _save(slug, topics)
    return topic


def remove_topic(slug: str, tid: str) -> None:
    _save(slug, [t for t in get_topics(slug) if t["id"] != tid])


def teach(term: str, audience: str, slug: str | None = None) -> dict:
    """Audience-tailored lesson. Cached into the saved topic when one exists."""
    from config.settings import get_settings

    audience = audience if audience in _TEACH_SYSTEM else "adult"
    tid = _topic_id(term)

    if slug:
        for t in get_topics(slug):
            if t["id"] == tid and t.get("taught", {}).get(audience):
                return {"text": t["taught"][audience], "cached": True}

    if not get_settings().has_llm_key():
        return {"error": "Teaching needs an AI key — add one on the Settings page."}

    from src.analysis.llm_providers import LLMProvider
    result = LLMProvider().generate(
        _TEACH_SYSTEM[audience], f"Teach: {term}", max_tokens=400)
    if result is None:
        return {"error": "Couldn't reach the AI right now — try again in a minute."}

    text = result.text.strip()
    if slug:
        topics = get_topics(slug)
        for t in topics:
            if t["id"] == tid:
                t.setdefault("taught", {})[audience] = text
                _save(slug, topics)
                break
    return {"text": text, "cached": False}
