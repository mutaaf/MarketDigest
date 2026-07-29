# AGENTS.md — start here (human or AI)

The indexed entry point for anyone — a person, a Claude session, any future
harness — working in this repository. Read this before changing anything.

## What this repository actually is (three products, one repo)

| System | What it is | Users | Entry points |
|---|---|---|---|
| **Market Digest / Signal Forge** | Trading analysis: digests to Telegram, day-trade scoring, options flow, paper trading, backtesting | The owner (expert) | `/` Command Center UI, `scripts/run_digest.py` |
| **Compass** | Family investing app: portfolios, health grades, buy-next recommendations, retirement, AI assistant, knowledge map | Non-technical family members, iPhone/iPad-first | `/compass` (own PWA identity + layout) |
| **Family Portal** | Windows-XP-style landing page + auth gateway on port 80 | Whole family | `scripts/family_portal.py` serving `~/projects/family-portal/` (SEPARATE repo — see coordination rules) |

One FastAPI server (`ui/server.py`, port 8550) serves the first two; the
portal is a separate process on port 80 that deep-links into it.

## Map of the code

**Backend (Python 3.12, `.venv/bin/python` ALWAYS — system pip is locked)**
- `config/settings.py` — config loader. Universe functions: `get_all_yfinance_tickers()`
  (digest/day-trade universe — do NOT grow this casually, every symbol is fetched by
  digests), `get_etf_universe()`, `get_compass_universe()` (stocks + compass_stocks +
  ETFs + crypto; Compass-only).
- `config/instruments.yaml` — groups: `us_stocks` (~50, day-trade + Compass),
  `compass_stocks` (~244, Compass-only, sector-tagged), `etfs` (~111,
  category/asset_class-tagged), `crypto`, plus forex/commodities/indices for digests.
- `src/portfolio/` — the Compass domain. One file per concern: `store` (JSON
  persistence + CSV), `valuation` (pricing w/ per-symbol fallback + crypto symbol
  mapping), `analyzer` (allocation, geography, market-cap, beta/yield — cached-data
  based), `health` (plain-English graded factors), `recommender` (gap × grade ranking,
  snapshots to logs/compass_recs/), `overlap`, `retirement` (deterministic + Monte
  Carlo), `watchlist`, `history` (daily value snapshots), `learn` (knowledge map +
  teach-me), `extract` (screenshot/text → holdings via LLM vision), `compare`.
- `src/analysis/` — scoring engines. `fundamentals.py` (stock quality, cache key
  `fundamentals:v2:`), `etf_scorer.py`, `daytrade_scorer.py` (`score_to_grade` is THE
  shared A–F scale), `llm_providers.py` (Anthropic→OpenAI→Gemini fallback; `generate`
  is prompt-hash-cached 2h — NEVER use for live chat without unique prompts;
  `generate_with_image` for vision).
- `src/fetchers/` — data sources. `yfinance_fetcher` (prices), `etf_data` (profiles,
  24h cache + stale fallback). Everything caches via `src/cache/manager.py`
  (memory + file, `get_stale()` for graceful degradation).
- `ui/routes/` — one file per API group. Compass lives in `portfolio.py` (two
  routers: `/api/portfolio/*` and `/api/compass/*`), `etf.py`, `assistant.py`.
- `scripts/compass_alerts.py` — Telegram watchlist alerts (weekday 15:15) + weekly
  family summary (Sun 17:00) + daily value history recording.

**Frontend (React 18 + Vite + Tailwind, `ui/frontend/`)**
- `src/pages/Compass*.tsx` — one page per Compass surface; everything else is the
  trading Command Center.
- `src/components/compass/` — the Compass design system: `ui.tsx` (Sheet at z-[70],
  GradeChip, ScoreRing, MoneyInput/UnitInput with live $/comma formatting, useCountUp,
  usePortfolioSelection — validates stored selection against the live list before any
  fetch), `Term.tsx` (tap-to-define: glossary → localStorage → AI, layered caching),
  `CompassLayout.tsx` (owns PWA identity swap: title/manifest/apple-touch-icon),
  `SmartImport.tsx`, `RulesOfThumb.tsx`, `retirementMath.ts` (client mirror of server
  projection — keep them in sync).

## Non-negotiable conventions

1. **UX principles** live in `docs/COMPASS_PLAN.md` ("UX Principles" section) — mobile
   (390px) first, four explicit states per data view (loading skeleton / friendly
   empty / plain-English error with retry / stale-with-banner), partial results over
   all-or-nothing (`warnings` arrays), 44px touch targets, 16px input font on touch
   (iOS zoom), sheets above the tab bar, every jargon term wrapped in `<Term>`.
2. **Money always formats** ($ + commas) via MoneyInput/`money()`; units get suffixes.
3. **Grades + reasons, never confidence percentages.** Recommendation sets snapshot to
   `logs/compass_recs/` for later grading.
4. **Personal data never enters git**: `data/portfolios/`, `data/watchlists/`,
   `data/history/`, `data/learn/`, `logs/` are gitignored. Check before `git add -A`.
5. **Digest isolation**: anything added for Compass must not enlarge
   `get_all_yfinance_tickers()` or digest latency.

## Workflows

- **Run/deploy**: the server runs as launchd agent `com.marketdigest.ui` (RunAtLoad +
  KeepAlive). After backend changes: `launchctl kickstart -k gui/$UID/com.marketdigest.ui`.
  After frontend changes: `cd ui/frontend && npm run build` first, then kickstart.
  Server binds 0.0.0.0:8550; family devices use the LAN address / `azizfamily.local`.
- **Verify before claiming done**: `npx tsc --noEmit` + build for frontend; exercise
  endpoints with curl using a SCRATCH portfolio (create → test → DELETE it); browser-
  check at 390px AND 820px (iframe trick if the window won't resize). Never test
  against the family's real portfolios.
- **Checks**: `.venv/bin/python -m ruff check .` and `pytest tests/ -q`. A `pre-push`
  git hook runs both against the EXACT pushed tree (`git archive HEAD`) — this exists
  because working-tree checks once missed a broken committed file.
- **Scheduled jobs** (launchd, installed by `scripts/setup_launchd.py`): four digests,
  compass-daily (alerts + history), compass-weekly (family summary),
  `com.azizfamily.portal` (port 80), `com.azizfamily.mdns` (hostname publishing).

## Multi-session coordination (IMPORTANT)

Multiple Claude sessions work this codebase simultaneously from the SAME checkout:
- One session owns Compass/Market Digest (this doc's scope).
- Another owns the Family Portal (`scripts/family_portal.py` + the separate
  `~/projects/family-portal/` repo). **Do not commit another session's in-progress
  files** — commit your own files explicitly by path, never bare `git add -A`
  when foreign modifications are present (`git status` first). If their committed
  code breaks lint, fix the minimal issue in place but let their session own the file.
- The pre-push hook protects both sessions; keep it intact.

## Current state & what's next

`docs/COMPASS_PLAN.md` is the living roadmap: phase history, PRD coverage checklist
(items done/remaining), and Phase 5 (multi-family hosting: VPS + Docker + per-family
auth) which is SAVED and waiting on the owner's hosting/domain decisions.
`docs/CHANGELOG.md` records shipped work. The owner's Claude memory
(`~/.claude/projects/-Users-mutaafaziz-projects-market-digest/memory/`) carries
cross-session context.
