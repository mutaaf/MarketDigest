# Market Digest - AI Knowledge Base

> Automated financial market digest platform — fetches market data, runs technical analysis, generates Telegram digests with optional LLM commentary, and tracks day trade pick performance.

**See Also:**
- [KNOWLEDGE_BASE.md](./KNOWLEDGE_BASE.md) - Detailed technical reference
- [docs/DECISIONS.md](./docs/DECISIONS.md) - Architecture decision records
- [docs/CHANGELOG.md](./docs/CHANGELOG.md) - Version history and changes

## Project Overview

### What This Is
A full-stack market digest automation system that fetches real-time data from 6+ sources (yfinance, TwelveData, Finnhub, FRED, NewsAPI, Fear&Greed), runs multi-timeframe technical analysis (daily/weekly/monthly RSI, pivots, trend detection, sentiment scoring), fetches equity fundamentals, and delivers formatted digests to Telegram. Includes a React web UI ("Command Center") for configuration, digest preview, multi-timeframe scorecards, and day trade performance tracking via the Retrace system.

### Why It Exists
- Consolidate pre-market and post-market analysis into a single automated workflow
- Eliminate manual data gathering across multiple financial platforms
- Provide scored day trade picks with entry/target/stop levels across three timeframes
- Analyze equity fundamentals (valuation, profitability, growth, financial health)
- Track pick performance over time to tune scoring weights and prompts

### Who It's For
Active traders who want automated daily market briefs delivered to Telegram, with the ability to review and improve pick accuracy over time.

---

## Architecture Overview

### Tech Stack
| Layer | Technology | Version |
|-------|------------|---------|
| Backend | Python | 3.12 (Homebrew venv) |
| Web API | FastAPI + uvicorn | >=0.115.0 |
| Frontend | React + TypeScript | 18.3 |
| Build | Vite | 6.x |
| Styling | Tailwind CSS | 3.4 |
| Data | yfinance, TwelveData, Finnhub, FRED, NewsAPI | Various |
| LLM | Anthropic, OpenAI, Google Gemini | Claude Haiku 4.5 / GPT-4o-mini / Gemini 2.0 Flash |
| Delivery | python-telegram-bot | >=21.0 |
| Scheduling | macOS launchd | Native |
| Cache | Memory + JSON files | Custom dual-tier |

### Key Design Decisions
1. **No database** — all persistence is YAML configs + JSON files. Simple, portable, no setup.
2. **Multi-provider LLM fallback** — Claude -> OpenAI -> Gemini. First available key wins.
3. **Dual-tier caching** — in-memory + file-backed JSON with TTL. Stale fallback if fetch fails.
4. **YAML-backed config** — instruments, prompts, digests, scoring weights all editable via UI with write-back.
5. **Telegram delivery** — auto-splits at 4096 chars, HTML formatted, multi-recipient.
6. **Retrace system** — snapshots every daytrade digest, grades picks against actual next-day prices.
7. **Multi-timeframe scoring** — Day Trade (daily), Swing (weekly), Long Term (monthly) with separate weight configs.
8. **Equity fundamentals** — valuation/profitability/growth/health scoring via yfinance + Finnhub fallback, cached 6h.
9. **Auto-restart server** — `start.command` restarts uvicorn on crash with exponential backoff (2s→60s cap).

---

## Directory Structure

```
market-digest/
├── config/
│   ├── settings.py          # Dataclass config loader (reads .env + YAML)
│   ├── instruments.yaml     # 84 instruments (forex, indices, commodities, crypto, stocks, FRED)
│   ├── prompts.yaml         # 25 LLM prompt sections + provider config
│   ├── digests.yaml         # Digest sections, modes, schedules
│   └── scoring.yaml         # Scoring weights: daytrade, swing, longterm (equity + non-equity)
├── src/
│   ├── analysis/            # Technicals, sentiment, LLM, scoring (daytrade/swing/longterm), fundamentals
│   ├── cache/manager.py     # Dual-tier cache (memory + file JSON)
│   ├── delivery/            # Telegram bot delivery
│   ├── digest/              # Morning, afternoon, weekly, daytrade builders + formatter
│   ├── fetchers/            # yfinance, TwelveData, Finnhub, FRED, NewsAPI, Fear&Greed
│   ├── retrace/             # Snapshot, grading, scoring config, versioning
│   └── utils/               # Logging, rate limiting, timezone
├── ui/
│   ├── server.py            # FastAPI app (11 route groups, 60 endpoints)
│   ├── models.py            # Pydantic models
│   ├── routes/              # 11 route files
│   └── frontend/            # React + Vite + Tailwind (10 pages)
├── scripts/
│   ├── run_digest.py        # CLI entry point
│   ├── start_ui.py          # One-command UI launcher
│   ├── setup_launchd.py     # macOS scheduled daemon setup
│   ├── test_apis.py         # API connection tester
│   └── test_telegram.py     # Telegram delivery tester
├── logs/                    # Digest history, retrace snapshots, app logs
├── cache/                   # File-backed JSON cache
└── requirements.txt         # Python dependencies
```

---

## Key Files Reference

### Config Loader (`config/settings.py`)
Singleton dataclass that reads `.env` (API keys, timezone, log level) and `instruments.yaml`. Key functions: `get_settings()`, `reload_settings()`, `update_env_var()`, `save_instruments()`, `get_all_yfinance_tickers()`.

### Digest Builder (`src/digest/builder.py`)
Orchestrator that initializes all fetchers, fetches prices/forex/commodities/crypto/news, runs analysis, and provides data dicts to digest templates. Each digest type calls `builder.fetch_*()` then formats output.

### LLM Analyzer (`src/analysis/llm_analyzer.py`)
Loads prompts from `config/prompts.yaml` (hardcoded fallbacks for 25 sections including `multi_tf_outlook` and `fundamentals_analysis`). Builds context per section, calls LLM via `llm_providers.py` with 3-provider fallback chain. Responses cached for 2 hours.

### Daytrade Scorer (`src/analysis/daytrade_scorer.py`)
Scores instruments 0-100 by weighted composite: RSI zone (20%), trend alignment (15%), pivot proximity (20%), ATR volatility (20%), volume ratio (15%), gap analysis (10%). Weights loaded from `config/scoring.yaml`.

### Multi-Timeframe Scorer (`src/analysis/multi_tf_scorer.py`)
Swing scorer (weekly technicals: RSI 25%, trend 30%, pivot 25%, ATR 20%) and long-term scorer (monthly technicals + fundamentals for equities at 60% weight). Both reuse `score_to_grade()` from daytrade_scorer. Non-equity instruments get 100% technical weights for long-term.

### Fundamentals Analyzer (`src/analysis/fundamentals.py`)
Fetches financial statement data (yfinance primary, Finnhub fallback) cached 6h. Scores across 4 dimensions (valuation, profitability, growth, health) each 0-100. Composite = equal-weight average. Equity-only — returns `None` for forex/commodities/crypto.

### Retrace Snapshot (`src/retrace/snapshot.py`)
Saves full daytrade digest data (picks, prices, weights, sentiment) to `logs/retrace/YYYY-MM-DD.json` after every run. Used by the grader to compare picks against actual next-day prices.

### FastAPI Server (`ui/server.py`)
Registers 11 route groups (60 endpoints). Frontend served as static files from `ui/frontend/dist/`. Runs on port 8550.

---

## Common Tasks

### Running the UI
```bash
.venv/bin/python scripts/start_ui.py
```
Builds frontend, starts uvicorn on port 8550, opens browser.

### Running a Digest (CLI)
```bash
# Dry run (print to console)
.venv/bin/python scripts/run_digest.py --type daytrade --mode facts --dry-run

# Send to Telegram
.venv/bin/python scripts/run_digest.py --type morning --mode full

# With action items
.venv/bin/python scripts/run_digest.py --type afternoon --mode both --action-items
```
Types: `morning`, `afternoon`, `weekly`, `daytrade`
Modes: `facts` (data only), `full` (data + LLM analysis), `both` (sends facts then full)

### Testing API Connections
```bash
.venv/bin/python scripts/test_apis.py
.venv/bin/python scripts/test_telegram.py
```

### Installing Dependencies
```bash
.venv/bin/pip install -r requirements.txt
cd ui/frontend && npm install
```

### Setting Up Scheduled Runs (macOS)
```bash
.venv/bin/python scripts/setup_launchd.py
```
Creates launchd plists for: morning (6:30 AM CT), afternoon (4:30 PM CT), weekly (Fri 5:30 PM CT), daytrade (8:15 AM CT).

---

## Known Considerations

1. **Always use `.venv/bin/python`** — system pip requires `--break-system-packages` flag
2. **yfinance is the primary data source** — free, no key needed, 2-min cache TTL
3. **LLM keys are optional** — without them, digests run in `facts` mode only (no analysis text)
4. **Telegram message limit is 4096 chars** — formatter auto-splits, but section headers are used as split points
5. **`SQ` ticker may show as delisted** — yfinance intermittent issue, doesn't affect other tickers
6. **Cache files accumulate in `cache/`** — can be cleared via UI (Cache page) or manually
7. **Config changes via UI are immediate** — YAML files are written directly, `reload_settings()` refreshes in-memory state
8. **Retrace grading requires next trading day** — grading a same-day snapshot will return "pending"
9. **Scoring weights must sum to 1.0** — validated on save, UI shows real-time sum. Three weight sets: daytrade (6 keys), swing (4 keys), longterm_equity (5 keys with 60% fundamentals), longterm_non_equity (4 keys).
10. **No database** — all state is in YAML configs, JSON logs, and file cache. Portable but not concurrent-safe.
11. **Detail scorecard uses 2y history** — `/api/scorecard/{symbol}` fetches 2 years for monthly analysis. `/api/scorecard/all` uses 6mo (enough for swing, skips long-term) to stay fast.
12. **Fundamentals are equity-only** — forex, commodities, and crypto get `fundamentals: null`. Long-term scoring for non-equities uses 100% technical weights.
13. **Server auto-restarts** — `start.command` wraps uvicorn in a restart loop with exponential backoff (2s→60s). Ctrl+C exits cleanly.

---

## Deployment

- **Local only** — runs on macOS with launchd scheduling
- **UI (dev)**: `.venv/bin/python scripts/start_ui.py` (builds frontend, starts FastAPI on port 8550)
- **UI (double-click)**: `start.command` — one-click launcher with auto-restart on crash
- **CLI**: `.venv/bin/python scripts/run_digest.py` with flags
- **Scheduled**: macOS launchd plists in `launchd/` directory
- **No Docker, no cloud deployment** — designed for single-user local operation

---

## Future Roadmap Ideas

1. Backtesting engine — run historical scoring weights against past data
2. Multi-user support with per-user configs
3. Additional data sources (Bloomberg, Alpha Vantage)
4. Email delivery option alongside Telegram
5. Interactive charts in the web UI
6. Git-based config versioning (currently file-based)
7. Docker containerization for portability
8. Automated scoring weight optimization based on retrace performance
