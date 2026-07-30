# Compass Investing — Implementation Plan

> **Status (July 30, 2026): COMPLETE for single-household use.** Every buildable PRD
> item has shipped and been verified — see "PRD Coverage" below. The app runs always-on
> (launchd), installs to phones as a PWA, and the family is actively using it.
> Remaining by design only:
> - **Phase 5 (ten families)** — awaiting the owner's hosting/domain/auth decisions.
> - **DCF / intrinsic value / moat ratings** — deliberately deferred (analyst targets
>   serve as the value signal until the core proves out).
> - **Recommendation-performance dashboard** — snapshots have been recording to
>   logs/compass_recs/ since day one; build the grading view once months of data exist.
> Formerly-listed Phase 4 items now done elsewhere: weekly Telegram digest
> (compass-weekly job), overlap analysis (Ideas), access gate (family portal passcode).

> "Know exactly what to buy next." A long-term investor advisor built inside Market Digest,
> designed for a non-technical user. Based on the Compass Investing PRD (July 2026).

**Strategy:** Reuse Market Digest's analysis engines (fundamentals, long-term A–F scoring,
LLM layer, fetcher/cache infra). Skip the PRD's Next.js/Supabase/Vercel stack entirely —
single household, file-based persistence, no auth. Ship in phases where each phase is
independently usable.

**Scope guardrail:** The PRD's own "MVP v1" cut is the target for Phase 1. Everything else
is deliberately later. We surface **grades and reasons**, not fabricated "94% confidence"
numbers — the Retrace pattern (track recommendations against reality) keeps us honest.

## UX Principles (apply to every Compass surface)

1. **Mobile-first.** Every page is designed at 390px width first, then enhanced for
   desktop. Touch targets ≥ 44px, bottom-sheet patterns over modals, no hover-only
   affordances, `env(safe-area-inset-*)` respected.
2. **Graceful in failure.** Every data view has four explicit states: loading (skeleton,
   not spinner-on-white), empty (friendly guidance on what to do next), error (plain
   words — "We couldn't reach the market data service. Your portfolio is safe; pull to
   retry." — never a stack trace or "Error 500"), and stale (banner: "Prices as of
   2:04 PM — showing last saved data"). Stale cached data is always preferred over a
   blank screen (the cache layer's `get_stale` exists for exactly this).
3. **Partial results over all-or-nothing.** If 2 of 30 symbols fail to fetch, show 28
   with a note — never fail the whole page. API responses carry a `warnings` list.
4. **Plain English everywhere.** No jargon without an inline explanation. Numbers get
   context ("0.03% — that's $3/year per $10,000 invested").
5. **Nothing destructive without undo or confirm.** Deleting a holding asks once, in
   words that say what happens.
6. **Every element earns its place; every term is definable.** Modals sit above all
   chrome, contrast meets WCAG on every state, interactive elements react to touch.
   Any jargon anywhere is wrapped in `<Term>` — tap for a plain-English definition,
   served instantly from the built-in glossary, then localStorage, then the AI teach
   endpoint (each layer caching for the next).

---

## Phase 0 — Data Foundations

*Everything later depends on instrument metadata and ETF data that don't exist yet.*

### Work items
1. **ETF universe** — new `etfs` group in `config/instruments.yaml` (~100 ETFs: broad US,
   international, bonds, sectors, dividend, REIT, growth/value). Each entry: `symbol`,
   `name`, `category` (us_broad / intl / bond / sector:tech / dividend / reit / ...),
   `enabled`.
2. **Sector/type taxonomy** — add `sector` and `asset_class` fields to each stock entry in
   `instruments.yaml` (backfill once from yfinance `info.sector`, then it's static config).
   Extend `get_all_yfinance_tickers()` in `config/settings.py` to carry the new fields.
3. **ETF data fetcher** — new `src/fetchers/etf_data.py` using yfinance `funds_data` +
   price history: expense ratio, dividend yield, AUM, top-10 holdings, sector weights,
   1/3/5/10-year returns, since-inception return, volatility (annualized stdev). Cached
   24h via existing `CacheManager` (pattern: `src/analysis/fundamentals.py`).
4. **ETF scorer** — new `src/analysis/etf_scorer.py`: Risk / Safety / Growth / Income /
   Diversification sub-scores (0–100) + overall score + A–F grade via the shared
   `score_to_grade()`. Config-backed weights in `config/scoring.yaml` (new `etf` block).
5. **Fundamentals gaps** — extend `src/analysis/fundamentals.py` with PEG, ROIC, dividend
   yield, payout ratio, analyst mean target (`info.targetMeanPrice`), beta. Widen
   `is_equity_symbol()` handling so ETFs route to the ETF scorer instead of returning None.

### Outcomes (done when)
- [ ] `instruments.yaml` has ~100 ETFs and every stock has sector + asset_class
- [ ] `/api/etf/{symbol}` returns full ETF profile with scores in < 2s (cached)
- [ ] Fundamentals payload includes PEG, ROIC, dividend yield, analyst target
- [ ] Existing digests/scorecards unaffected (ETFs excluded from daytrade scoring)

**Estimate:** 1–2 working sessions. No UI work in this phase.

---

## Phase 1 — Portfolio Core + "What Should I Buy Next?" (PRD MVP v1)

*The feature that makes her say "I need this."*

### Data model
`data/portfolios/{name}.json` (new dir, one file per person — no DB, no auth):
```json
{
  "name": "her-name",
  "cash": 5000.00,
  "holdings": [
    {"symbol": "VOO", "shares": 40, "cost_basis": 380.50, "acquired": "2024-03-01", "account": "brokerage"}
  ],
  "targets": {},
  "updated": "2026-07-28T10:00:00"
}
```

### Work items
1. **Portfolio module** — new `src/portfolio/`:
   - `store.py` — load/save/validate portfolio JSON, CSV import (broker-export-tolerant:
     map common column names, skip junk rows)
   - `valuation.py` — current value, day change, total gain/loss per holding + total,
     using existing yfinance fetcher (2-min cache)
   - `analyzer.py` — allocation breakdown by asset class / sector / market cap / US-vs-intl.
     For ETF holdings, look through via sector weights from the ETF fetcher. Weighted
     expense ratio, weighted dividend yield, weighted beta.
   - `health.py` — Diversification Score (sector concentration via HHI, single-position
     concentration, asset-class spread, US/intl split) + overall Portfolio Grade A–F with
     per-factor plain-English explanations
   - `recommender.py` — "what should I buy next": rank the enabled universe by
     `long-term score (existing multi_tf_scorer / etf_scorer) × underweight-fit ×
     valuation attractiveness`; exclude already-concentrated positions; return top N with
     reasons ("You're underweight international; VXUS grade A-, expense ratio 0.07%")
2. **API** — new `ui/routes/portfolio.py`: CRUD holdings, CSV upload, `GET /summary`,
   `GET /health`, `GET /recommendations`, `GET /compare?a=VOO&b=VTI` (works for any mix of
   ETF/stock — normalizes to a common metric table + LLM one-paragraph verdict via
   existing `MarketAnalyzer` pattern)
3. **UI** — new "Compass" nav group in `Sidebar.tsx` / `BottomNav.tsx` with three pages:
   - `CompassPortfolio.tsx` — holdings table, add/edit/CSV import, value + P&L, allocation
     donuts (sector / asset class / geography)
   - `CompassIdeas.tsx` — health grade card with factor breakdown, then ranked buy
     recommendations with reasons
   - `CompassCompare.tsx` — two-ticker picker, side-by-side metric table with
     better-value highlighting, plain-English verdict

### Outcomes (done when)
- [ ] A portfolio can be entered manually or via CSV in under 5 minutes
- [ ] Portfolio page shows value, gain/loss, and 3 allocation breakdowns
- [ ] Health page shows an A–F grade with ≥4 explained factors
- [ ] ≥3 personalized recommendations, each with a why in plain English
- [ ] Any two tickers comparable in under 1 minute (PRD success criterion)

**Estimate:** 3–4 working sessions. This is the demo-to-wife milestone.

---

## Phase 2 — Targets, Watchlist, Retirement

### Work items
1. **Target allocation** — `targets` block in portfolio JSON (e.g. US 60 / Intl 20 /
   Bonds 10 / REIT 10). Actual-vs-target bars with over/underweight flags; drift feeds
   directly into the Phase 1 recommender (replaces its heuristic underweight-fit).
   Editable in `CompassPortfolio.tsx` with must-sum-to-100 validation (same pattern as
   scoring weights UI).
2. **Watchlist** — `data/watchlists/{name}.json`: symbol, desired buy price, notes.
   Page shows current price, % to buy price ("7% above your buy price"), current A–F
   grade, and recent headlines via existing NewsAPI fetcher. New `CompassWatchlist.tsx`.
3. **Retirement planner** — pure math, no new data: inputs (age, retirement age, assets
   pre-filled from portfolio, monthly contribution, expected return, inflation) →
   deterministic projection curve + Monte Carlo (1000 runs on historical-ish return/vol)
   for probability of success + 4%-rule safe-withdrawal estimate. New
   `src/portfolio/retirement.py` + `CompassRetire.tsx` with a projection chart.
4. **Recommendation tracking (Retrace for Compass)** — snapshot each recommendation set
   to `logs/compass_recs/`; a simple view later shows how past recommendations performed.
   Cheap to add now, builds trust in the engine over time.

### Outcomes (done when)
- [ ] Targets editable; over/underweights visible and driving recommendations
- [ ] Watchlist alerts visually when a symbol crosses its buy price
- [ ] Retirement page answers "am I on track?" with a probability and a chart
- [ ] Every recommendation set is snapshotted for later grading

**Estimate:** 2–3 working sessions.

---

## Phase 3 — The Wife Experience (simple mode, assistant, access)

*Compass stops being a tab in your trading app and becomes her app.*

### Work items
1. **Compass-only layout** — `/compass/*` route group with its own minimal layout: Home,
   Portfolio, Ideas, Watchlist, Retire, Learn, Ask. None of the trader pages, no jargon,
   larger type, mobile-first. Your existing full app stays at `/`. Her bookmark is
   `http://<mac-hostname>.local:8550/compass`.
2. **Compass Home** — the PRD dashboard: portfolio value, cash, today's change, grade,
   diversification score, target-vs-actual mini-bars, retirement progress, top
   recommendation of the day. One screen, no scrolling on desktop.
3. **AI assistant ("Ask")** — new streaming multi-turn endpoint
   `ui/routes/assistant.py` (`POST /api/assistant/chat`): reuses `llm_providers.py`
   fallback chain but **bypasses the prompt-hash cache** (it would break conversation);
   context = her portfolio summary + health factors + relevant scorecard/ETF data for any
   tickers mentioned. System prompt: beginner-friendly, always explains terms, never gives
   pressure-y advice, cites the numbers it used. Suggested-question chips ("Am I
   diversified?", "Compare VOO and VTI", "What should I do with $5,000?").
4. **Education ("Learn")** — ~15 static beginner explainers (ETF, expense ratio, beta,
   drawdown, DCF, compounding...) as content, plus an "explain this like I'm new" button
   that routes any term to the assistant. Glossary terms hyperlinked from Compass pages.
5. **LAN access + guard** — uvicorn binds `0.0.0.0`, startup prints the LAN URL; optional
   4-digit PIN gate on `/compass` (cookie, stored in `.env`) so it's not wide open on the
   network. Profile switcher (your portfolio vs hers) as a simple dropdown — files, not
   auth.

### Outcomes (done when)
- [ ] She can open Compass on her phone/laptop via the Mac's LAN address
- [ ] Home answers "how am I doing / what should I buy next" in one glance
- [ ] Assistant answers portfolio-aware questions in plain English, streaming
- [ ] She completes add-holding → see grade → read recommendation → ask a question
      without help (the real acceptance test)

**Estimate:** 3–4 working sessions.

---

## PRD Coverage (evaluated July 28, 2026)

**Done** — portfolio tracking (manual/CSV/screenshot/paste import), health grade +
diversification score, buy-next recommendations with reasons, target vs actual
allocation with presets, ETF universe (~110) with scores/grades, stock quality scores,
two-ticker comparison with verdict, watchlist with buy-price alerts, retirement planner
with Monte Carlo, AI assistant, education center, onboarding wizard, Telegram alerts,
PWA home-screen app, all PRD MVP-v1 success criteria except accounts.

**Remaining from the PRD, prioritized:**
1. ~~Browse pages for the ETF database~~ — DONE (/compass/explore with detail sheets).
2. ~~Richer portfolio analytics~~ — DONE (weighted beta/yield, geography, market-cap,
   style breakdowns; "Portfolio character" card).
3. ~~Overlap analysis~~ — DONE (stock-in-fund + fund-pair via top-10 holdings, shown
   on Ideas as "Owning the same thing twice").
4. **Stock universe expansion** — ~50 stocks today vs PRD's ~250. Config work + sector
   tagging.
5. ~~Watchlist news~~ — DONE (tap a watchlist item → recent financial headlines).
6. ~~ETF "Pros/Cons/Best For/Similar"~~ — DONE (LLM-written, 7-day cache, similar funds grade-ranked with compare links).
7. ~~Performance over time chart~~ — DONE ("Your journey" card on Portfolio; grows from daily snapshots (weekday
   compass-daily job → data/history/, plus GET /{name}/history endpoint); chart UI
   once a few weeks of data exist.
8. **Fair value / intrinsic value / DCF and moat ratings** — deliberately deferred;
   analyst targets serve as the value signal until the core proves out.
9. **Accounts** — Phase 5 (per-family auth on hosted deployment). Note: the family
   portal (separate repo) has since added its own passcode gate on port 80.

**Deliberately not building:** confidence percentages, licensed data feeds,
Next.js/Supabase stack.

## Phase 5 — Ten Families (multi-household expansion)

*Everything before this phase assumes one household on one Mac. Serving 10 families
means leaving the LAN — which makes hosting, auth, and data isolation real requirements,
not overkill.*

### What changes and what doesn't
- **Keeps:** the FastAPI + React app, all the analysis engines, file-per-portfolio
  simplicity (10 families ≈ 20-30 portfolios — still no Postgres needed; SQLite or
  namespaced JSON dirs are fine).
- **Must add:**
  1. **Hosting** — a $5-10/mo VPS (Hetzner/DigitalOcean) or Fly.io app running the
     existing server in Docker. The Mac stays your dev machine, not the family server.
  2. **Auth** — per-family login. Simplest robust option: one shared passphrase per
     family mapping to a family namespace (`data/families/{family}/portfolios/`),
     issued as a signed cookie. No password-reset flows, no email infra. Upgrade path
     to magic-link email auth if it ever grows past friends-and-family.
  3. **Data isolation** — every portfolio/watchlist/retirement route scoped to the
     authenticated family's directory; the trading/digest admin routes locked to an
     admin passphrase (or simply not exposed on the public deployment).
  4. **TLS + domain** — Caddy in front (automatic HTTPS), one cheap domain.
  5. **Rate limiting + API-key hygiene** — yfinance is unauthenticated (fine), but the
     LLM keys are yours: cap assistant usage per family per day.
  6. **Backups** — nightly tar of `data/` to object storage (it's just small JSON).

### Decisions needed before building
- Hosting platform + budget (recommendation: Hetzner CX22, ~$4/mo, Docker Compose)
- Domain name
- Auth flavor: family passphrase (recommended for 10 known families) vs magic-link email
- Whether the public deployment is Compass-only (recommended) or includes the full
  Command Center

### Build order (est. 3-4 sessions)
1. Dockerfile + compose (app + Caddy), Compass-only route surface
2. Family auth middleware + namespaced data dirs + migration of existing portfolios
3. Per-family LLM usage caps; backup cron
4. Deploy, onboard family #2, iterate

## Phase 4 — Later / Optional

- ETF overlap matrix (top-10 holdings intersection weight between her ETFs)
- Recommendation performance dashboard (grade past picks, like Retrace)
- Weekly "Compass digest" to her own Telegram (reuses delivery layer)
- Country/style (growth-value) allocation breakdowns
- Fair-value / DCF estimates for stocks (PRD lists it; real modeling effort — punt until
  the core loop proves out)
- Broker import beyond CSV (Plaid etc. — only if manual upkeep becomes a real complaint)

---

## Explicitly out of scope (PRD items we're intentionally not building)

- **Accounts/auth/multi-tenant** — one household, profile files instead
- **Supabase/Postgres/Vercel** — file persistence, local hosting on the Mac
- **Licensed market data** — yfinance covers everything Phase 0–3 needs, free
- **Confidence percentages** — grades + reasons + tracked outcomes instead

## Sequencing summary

| Phase | Deliverable | Est. sessions | Demo moment |
|-------|-------------|--------------|-------------|
| 0 | ETF universe + metadata + scorers | 1–2 | `/api/etf/VOO` returns a graded profile |
| 1 | Portfolio, health, buy-next, compare | 3–4 | **Show her the recommendations** |
| 2 | Targets, watchlist, retirement | 2–3 | "Am I on track?" answered |
| 3 | Compass app, assistant, LAN access | 3–4 | **She uses it on her own phone** |
