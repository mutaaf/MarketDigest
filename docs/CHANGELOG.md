# Changelog

All notable changes to Market Digest.

## [Unreleased]

### Added
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
- 18 section prompt types with per-section customization
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
