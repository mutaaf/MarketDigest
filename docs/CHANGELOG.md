# Changelog

All notable changes to Market Digest.

## [Unreleased]

### Added
- **Compass feature-complete (July 29-30)**: 294-company stock database with Explore
  browsing (Funds | Stocks | Crypto tabs), personalized Compare verdicts ("for your
  portfolio" pick using the viewer's gaps/holdings/overlap), crypto as a first-class
  asset class end-to-end, live retirement-portfolio sync, 10 rules of thumb computed
  with the user's numbers, broker export navigator (15 brokers), screenshot/paste/CSV
  smart import with review step, persistent async Ask chats with 10MB storage GC,
  Learn knowledge map (AI-suggested topics + kid/adult teach-me), watchlist news,
  LLM fund pros/cons/best-for + similar funds, "Your journey" value history chart,
  family refresh button (5-min cooldown), PWA identity, iPhone/iPad touch polish,
  docs/AGENTS.md context layer for future agents/humans
- **Compass Investing** — a standalone long-term investor app at `/compass` with its own
  mobile-first layout (Home, Portfolio, Ideas, Ask, Watchlist, Retirement, Compare, Learn).
  Built for a non-technical user; reachable from any device on the home network.
  - Portfolio tracking: per-person JSON portfolios (`data/portfolios/`), manual entry +
    tolerant CSV import, live valuation, gain/loss, allocation by asset class and sector
    (with ETF look-through), weighted expense ratio
  - Portfolio health: A–F grade from five plain-English diversification checks
    (`src/portfolio/health.py`)
  - "What should I buy next?": gap-aware recommendation engine ranking graded ETFs/stocks
    against target allocation, every pick with explained reasons; each result set
    snapshotted to `logs/compass_recs/` for later grading
  - ETF database: ~110 ETFs in `instruments.yaml` with category/asset-class metadata,
    profiles via yfinance (expense ratio, yield, AUM, holdings, 1/3/5/10y returns,
    volatility) cached 24h, scored A–F (`src/analysis/etf_scorer.py`)
  - Two-ticker comparison (any mix of ETF/stock) with winner-highlighted metric table and
    deterministic plain-English verdict
  - Target allocation editor (must sum to 100%) feeding the recommender; watchlist with
    buy-price alerts; retirement planner with Monte Carlo probability of success
  - Ask Compass: portfolio-aware multi-turn assistant using the existing 3-provider LLM
    fallback chain (`ui/routes/assistant.py`); Learn page with 12 beginner explainers
  - Stocks in `instruments.yaml` now carry `sector` and `asset_class`; fundamentals
    gained PEG, dividend yield, payout ratio, beta, analyst target (cache key bumped to v2)
- **CI fixed**: `unusualwhales-python` pre-release specifier resolved + repo-wide ruff
  cleanup; first green backend run since March
- **Multi-timeframe scoring**: Day Trade (daily), Swing (weekly), Long Term (monthly) — each with separate configurable weights in `config/scoring.yaml`
- **Equity fundamentals analysis**: Fetches financial data (yfinance + Finnhub fallback, 6h cache), scores valuation/profitability/growth/health (0-100 each)
- **Weekly/monthly technical analysis**: `weekly_full_analysis()`, `monthly_full_analysis()`, `compute_monthly_pivots()`, `compute_monthly_atr()` in `src/analysis/technicals.py`
- **Multi-TF scorecard UI**: Timeframe tab selector (DT/Swing/LT), per-timeframe targets + S/R zones, fundamentals card with sub-score bars + collapsible highlights
- **Multi-TF digest integration**: Top 10 picks show Swing/LT grades inline; full mode adds LLM multi-TF outlook + fundamentals snapshot sections
- **Overview grade pills**: ScoreCard grid shows DT/SW/LT mini-badges per card
- **Server auto-restart**: `start.command` wraps uvicorn in restart loop with exponential backoff (2s→60s cap), resets after 30s healthy uptime, clean exit on Ctrl+C
- **New LLM sections**: `multi_tf_outlook` and `fundamentals_analysis` prompts in `config/prompts.yaml`
- Comprehensive project documentation (CLAUDE.md, KNOWLEDGE_BASE.md, docs/)

---

## [1.0.0] - February 2026

### Core Features

#### Digest Engine
- Morning digest (6:30 AM CT): overnight session recap, futures, forex, commodities, crypto, events, sentiment
- Afternoon digest (4:30 PM CT): close summary, movers, sentiment shift, forex, commodities, crypto
- Weekly digest (Fri 5:30 PM CT): week review, rankings, sector performance, technical levels
- Day trade picks (8:15 AM CT): scored intraday opportunities with entry/target/stop levels
- Action items extraction (3-5 actionable takeaways per digest)
- Modes: facts (data only), full (data + LLM analysis), both (sends facts then full)

#### Data Sources
- yfinance: primary price data (stocks, indices, commodities, daily forex) — free, no key
- TwelveData: real-time forex pairs + technicals — optional, paid
- Finnhub: company news, earnings calendar — optional, paid
- FRED: Federal Reserve economic indicators — optional, free
- NewsAPI: global news headlines + sentiment — optional, paid
- CNN Fear & Greed Index: sentiment gauge — no key needed

#### Technical Analysis
- RSI (14-period) with zone classification
- SMA/EMA crossover trend detection (bullish/bearish/neutral)
- Classic pivot points (PP, S1, S2, R1, R2)
- ATR volatility measurement
- Volume ratio (current vs average)
- Gap analysis (gap up/down %)
- Composite sentiment scoring (VIX + DXY + Fear&Greed + news)

#### LLM Analysis
- 25 section prompt types with per-section customization
- 3-provider fallback: Claude Haiku 4.5 -> GPT-4o-mini -> Gemini 2.0 Flash
- 2-hour response caching
- Configurable provider priority and model selection
- YAML-backed prompts with hardcoded fallback defaults

#### Day Trade Scoring
- 6-factor weighted composite: RSI (20%), trend (15%), pivot (20%), ATR (20%), volume (15%), gap (10%)
- Entry/target/stop level calculation from pivots + ATR
- Risk/reward ratio computation
- Signal generation (human-readable reasons)
- Top 10 picks + honorable mentions + avoid list

#### Delivery
- Telegram bot delivery with HTML formatting
- Auto message splitting at 4096 char limit
- Multi-recipient support
- Retry logic (3 attempts, exponential backoff)
- Dry-run mode (print to console)

#### Web UI — Command Center
- Dashboard: API health, cache stats, quick run buttons, history
- Onboarding: guided API key setup wizard
- Instruments: manage 46+ instruments (toggle, add, grouped by category)
- Prompts: edit 18 LLM section prompts, system prompt, provider config
- Data Sources: toggle + test each data source
- Digest Config: section selection, mode, schedule per digest type
- Run & Preview: interactive digest run with HTML preview + send
- Settings: timezone, log level, recipients, export/import config

#### Retrace — Performance Tracking
- Automatic snapshot on every daytrade digest run
- Pick grading against actual next-day OHLCV prices
- Win/loss/scratch outcome classification
- MFE (max favorable excursion) and MAE (max adverse excursion)
- R-multiple calculation
- Aggregate performance: win rate, by signal, by trend
- Externalized scoring weights (config/scoring.yaml)
- Config versioning with diff and rollback
- 4-tab UI: Performance, Scoring, Versions, Audit Trail

#### Infrastructure
- Dual-tier caching (memory + file JSON) with TTL and stale fallback
- NaN-safe serialization for market data
- Per-API rate limiting
- CT-centric timezone utilities
- macOS launchd scheduling (4 digest types)
- Config export/import (ZIP)

### Technical Decisions
- File-based persistence (no database) — see [ADR-001](./DECISIONS.md#adr-001-file-based-persistence-no-database)
- Multi-provider LLM fallback — see [ADR-002](./DECISIONS.md#adr-002-multi-provider-llm-fallback-chain)
- Dual-tier caching — see [ADR-003](./DECISIONS.md#adr-003-dual-tier-caching-memory--file)
- YAML-backed prompts — see [ADR-004](./DECISIONS.md#adr-004-yaml-backed-llm-prompts-with-hardcoded-fallbacks)
- Telegram delivery — see [ADR-005](./DECISIONS.md#adr-005-telegram-as-primary-delivery-channel)
- Externalized scoring — see [ADR-006](./DECISIONS.md#adr-006-externalized-scoring-weights-retrace-system)
- React + Vite + Tailwind — see [ADR-007](./DECISIONS.md#adr-007-react--vite--tailwind-for-frontend)
- macOS launchd scheduling — see [ADR-008](./DECISIONS.md#adr-008-macos-launchd-for-scheduling)

---

## Design Philosophy

### Principles
1. **Works out of the box** — hardcoded defaults for everything, zero-config startup
2. **Data first, analysis second** — facts mode always works, LLM mode is optional enhancement
3. **Fail gracefully** — stale cache fallback, provider fallback, section-level error handling
4. **Single-user simplicity** — file-based config, no auth, no multi-tenancy
5. **Portable** — no database, no Docker, just Python + Node + env vars
6. **Tunable** — every weight, prompt, section, and schedule is configurable via UI

### UX Decisions
- Apple-inspired design system (clean whites, subtle grays, blue accents)
- Mobile-friendly with bottom nav + overflow menu
- Toast notifications for async feedback
- Inline validation (e.g., scoring weights must sum to 100%)
- Dry-run as default for digest runs (prevent accidental Telegram sends)

---

## Future Considerations

### Potential Features
- [ ] Backtesting engine for historical weight optimization
- [ ] Email delivery alongside Telegram
- [ ] Interactive charts in web UI (TradingView or Recharts)
- [ ] Docker containerization
- [ ] Git-based config versioning
- [ ] Multi-user support with per-user configs
- [ ] Additional data sources (Bloomberg, Alpha Vantage)
- [ ] Automated scoring weight optimization from retrace data

### Technical Debt
- [ ] Cache directory cleanup automation (files accumulate)
- [ ] Concurrent write safety for config files
- [ ] Test suite (unit + integration)
- [ ] CI/CD pipeline
- [ ] Type annotations on all Python functions
