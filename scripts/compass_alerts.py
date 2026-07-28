#!/usr/bin/env python3
"""Compass Telegram alerts.

--mode daily   Watchlist buy-price alerts (weekday afternoons). A symbol at or
               below its buy price alerts at most once every 3 days.
--mode weekly  Family portfolio summary (Sunday evening): value, health grade,
               top recommendation per portfolio.
--dry-run      Print instead of sending.
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

STATE_PATH = PROJECT_ROOT / "logs" / "compass_alerts_state.json"
ALERT_COOLDOWN_DAYS = 3


def _load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def _should_alert(state: dict, slug: str, symbol: str) -> bool:
    last = state.get(slug, {}).get(symbol)
    if not last:
        return True
    try:
        days = (date.today() - date.fromisoformat(last)).days
        return days >= ALERT_COOLDOWN_DAYS
    except ValueError:
        return True


def build_daily_alerts() -> tuple[str | None, dict]:
    """Watchlist symbols at/below their buy price, across all portfolios.
    Returns (message, updated_state) — the caller persists state only after
    a real send, so dry runs never burn the alert cooldown."""
    from src.portfolio.store import list_portfolios
    from src.portfolio.watchlist import enrich_watchlist

    state = _load_state()
    sections = []
    for p in list_portfolios():
        slug = p["slug"]
        data = enrich_watchlist(slug)
        hits = [i for i in data["items"]
                if i.get("at_buy_price") and _should_alert(state, slug, i["symbol"])]
        if not hits:
            continue
        lines = [f"<b>{p['name']}</b>"]
        for i in hits:
            grade = f" (grade {i['grade']})" if i.get("grade") else ""
            lines.append(
                f"  🔔 <b>{i['symbol']}</b> is ${i['price']:.2f} — at or below your "
                f"${i['buy_price']:.2f} buy price{grade}"
            )
            state.setdefault(slug, {})[i["symbol"]] = date.today().isoformat()
        sections.append("\n".join(lines))

    if not sections:
        return None, state
    return ("🧭 <b>Compass — Price Alert</b>\n\n" + "\n\n".join(sections)
            + "\n\nOpen Compass to take a look before deciding anything."), state


def build_weekly_summary() -> str | None:
    """Sunday evening: one section per portfolio — value, grade, top pick."""
    from src.portfolio.analyzer import analyze_allocation
    from src.portfolio.health import assess_health
    from src.portfolio.recommender import recommend
    from src.portfolio.store import list_portfolios, load_portfolio
    from src.portfolio.valuation import value_portfolio

    portfolios = list_portfolios()
    if not portfolios:
        return None

    sections = []
    for p in portfolios:
        portfolio = load_portfolio(p["slug"])
        if portfolio is None:
            continue
        valuation = value_portfolio(portfolio)
        if not valuation["holdings"] and not valuation["cash"]:
            continue
        allocation = analyze_allocation(valuation)
        health = assess_health(allocation, valuation)

        lines = [f"<b>{portfolio['name']}</b> — ${valuation['total_value']:,.0f}"]
        if health.get("grade"):
            lines.append(f"  Health: {health['grade']} — {health['summary']}")
        try:
            recs = recommend(portfolio, valuation, allocation, limit=1)
            if recs["recommendations"]:
                top = recs["recommendations"][0]
                lines.append(f"  Next move: <b>{top['symbol']}</b> (grade {top['grade']}) — "
                             f"{top['reasons'][0]}")
        except Exception:
            pass  # summary still goes out without a pick
        sections.append("\n".join(lines))

    if not sections:
        return None
    return ("🧭 <b>Compass — Weekly Check-in</b>\n"
            f"<i>{datetime.now().strftime('%B %d, %Y')}</i>\n\n"
            + "\n\n".join(sections)
            + "\n\nDetails and reasons are in the app. Educational only — not "
              "licensed financial advice.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compass Telegram alerts")
    parser.add_argument("--mode", choices=["daily", "weekly"], required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    state = None
    if args.mode == "daily":
        # Record today's portfolio values first — powers the performance chart
        try:
            from src.portfolio.history import record_all
            print(f"[daily] Recorded value history for {record_all()} portfolio(s).")
        except Exception as e:
            print(f"[daily] History snapshot failed: {e}")
        content, state = build_daily_alerts()
    else:
        content = build_weekly_summary()

    if content is None:
        print(f"[{args.mode}] Nothing to send.")
        return

    if args.dry_run:
        print(content)
        return

    from src.delivery.telegram_bot import TelegramDelivery
    ok = TelegramDelivery().send_digest_sync(content)
    if ok and state is not None:
        _save_state(state)
    print(f"[{args.mode}] Sent: {ok}")


if __name__ == "__main__":
    main()
