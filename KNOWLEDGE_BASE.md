# Market Digest - Knowledge Base

> A comprehensive reference document for developers and AI agents working on this codebase.

**See Also:**
- [CLAUDE.md](./CLAUDE.md) - High-level overview for AI assistants
- [docs/DECISIONS.md](./docs/DECISIONS.md) - Architecture decision records (ADRs)
- [docs/CHANGELOG.md](./docs/CHANGELOG.md) - Version history and changes

---

## Quick Reference

### Tech Stack
| Layer | Technology | Version |
|-------|------------|---------|
| Runtime | Python | 3.12 (Homebrew venv at `.venv/`) |
| Web Framework | FastAPI | >=0.115.0 |
| ASGI Server | uvicorn | >=0.32.0 |
| Frontend | React | 18.3 |
| Frontend Build | Vite | 6.x |
| Styling | Tailwind CSS | 3.4 |
| TypeScript | TypeScript | 5.6 |
| Icons | lucide-react | 0.460 |
| HTTP Client | axios | 1.7 |
| Routing | react-router-dom | 6.28 |
| DnD | @dnd-kit | 6.1 / 8.0 |
| Data (Primary) | yfinance | >=0.2.31 |
| Data (Forex) | TwelveData | >=1.2.0 |
| Data (News) | Finnhub | >=2.4.0 |
| Data (Economic) | FRED API | >=0.5.0 |
| Data (Headlines) | NewsAPI | >=0.2.7 |
| Data Processing | pandas / numpy | >=2.1.0 / >=1.24.0 |
| NLP | TextBlob | >=0.17.0 |
| LLM (Primary) | Anthropic SDK | >=0.39.0 |
| LLM (Fallback 1) | OpenAI SDK | >=1.50.0 |
| LLM (Fallback 2) | Google Generative AI | >=0.8.0 |
| Delivery | python-telegram-bot | >=21.0 |
| Config | PyYAML / python-dotenv | >=6.0 / >=1.0.0 |
| Retry | tenacity | >=8.2.0 |
| Timezone | pytz | >=2023.3 |

### Key Commands
```bash
# Run the web UI (builds frontend, starts FastAPI on :8550)
.venv/bin/python scripts/start_ui.py

# Run a digest via CLI
.venv/bin/python scripts/run_digest.py --type daytrade --mode facts --dry-run
.venv/bin/python scripts/run_digest.py --type morning --mode full
.venv/bin/python scripts/run_digest.py --type afternoon --mode both --action-items
.venv/bin/python scripts/run_digest.py --type weekly --mode full

# Test API connections
.venv/bin/python scripts/test_apis.py
.venv/bin/python scripts/test_telegram.py

# Install dependencies
.venv/bin/pip install -r requirements.txt
cd ui/frontend && npm install

# Build frontend manually
cd ui/frontend && npm run build

# Set up macOS scheduled runs
.venv/bin/python scripts/setup_launchd.py

# Frontend dev server (hot reload)
cd ui/frontend && npm run dev
```

---

## Feature Inventory

| # | Feature | Status | Key Files |
|---|---------|--------|-----------|
| 1 | Morning Digest (6:30 AM CT) | Active | `src/digest/morning.py`, `config/digests.yaml` |
| 2 | Afternoon Digest (4:30 PM CT) | Active | `src/digest/afternoon.py` |
| 3 | Weekly Digest (Fri 5:30 PM CT) | Active | `src/digest/weekly.py` |
| 4 | Day Trade Picks (8:15 AM CT) | Active | `src/digest/daytrade.py`, `src/analysis/daytrade_scorer.py` |
| 5 | Action Items extraction | Active | `src/digest/action_items.py` |
| 6 | LLM Analysis (3-provider fallback) | Active | `src/analysis/llm_analyzer.py`, `src/analysis/llm_providers.py` |
| 7 | Technical Analysis (RSI, pivots, trend) | Active | `src/analysis/technicals.py` |
| 8 | Composite Sentiment Scoring | Active | `src/analysis/sentiment.py` |
| 9 | Trading Session Tracking | Active | `src/analysis/session_tracker.py` |
| 10 | Economic Calendar + Events | Active | `src/analysis/events.py` |
| 11 | Performance Rankings | Active | `src/analysis/performance.py` |
| 12 | Telegram Delivery (multi-recipient) | Active | `src/delivery/telegram_bot.py` |
| 13 | Dual-tier Caching (memory + file) | Active | `src/cache/manager.py` |
| 14 | Web UI — Command Center (10 pages) | Active | `ui/server.py`, `ui/frontend/src/` |
| 15 | Config Management (YAML + .env) | Active | `config/settings.py`, `ui/routes/settings.py` |
| 16 | Retrace — Snapshot + Grading | Active | `src/retrace/snapshot.py`, `src/retrace/grader.py` |
| 17 | Retrace — Scoring Config | Active | `src/retrace/scoring_config.py`, `config/scoring.yaml` |
| 18 | Retrace — Config Versioning + Rollback | Active | `src/retrace/versioning.py` |
| 19 | macOS launchd Scheduling | Active | `scripts/setup_launchd.py`, `launchd/` |
| 20 | Config Export/Import (ZIP) | Active | `ui/routes/settings.py` |
| 21 | Multi-Timeframe Scoring (Swing + LT) | Active | `src/analysis/multi_tf_scorer.py`, `config/scoring.yaml` |
| 22 | Equity Fundamentals Analysis | Active | `src/analysis/fundamentals.py` |
| 23 | Weekly/Monthly Technical Analysis | Active | `src/analysis/technicals.py` (weekly/monthly_full_analysis) |
| 24 | Multi-TF Scorecard UI (tabs, S/R zones) | Active | `ui/frontend/src/components/common/ScoreCardDetail.tsx` |
| 25 | Fundamentals Scorecard UI | Active | `ui/frontend/src/components/common/ScoreCardDetail.tsx` |
| 26 | Server Auto-Restart | Active | `start.command` (exponential backoff loop) |

---

## Architecture Documentation

### Data Flow — Digest Generation

```
CLI (run_digest.py) or API (/api/digests/run)
    │
    ▼
DigestBuilder (src/digest/builder.py)
    │── fetch_daytrade_universe() / fetch_prices() / fetch_forex() / ...
    │       │
    │       ▼
    │   Fetchers (yfinance, TwelveData, Finnhub, FRED, NewsAPI, Fear&Greed)
    │       │── Each fetcher: check cache → rate limit → fetch → cache set
    │       │── On failure: return stale cache if available
    │       ▼
    │   Raw price/indicator data dicts
    │
    ├── run_technicals() → RSI, SMA/EMA, pivots, trend per instrument
    ├── compute_sentiment() → composite 0-100 score
    ├── score_instrument() → daytrade opportunity ranking (weighted composite)
    │
    ▼
Digest Template (morning.py / afternoon.py / weekly.py / daytrade.py)
    │── Format data into Telegram HTML sections
    │── If mode=full: call LLM per section via llm_analyzer.py
    │       │── Load prompt from prompts.yaml (fallback to hardcoded)
    │       │── Build context dict (cross-section data)
    │       │── Call LLM provider (Claude → OpenAI → Gemini)
    │       │── Cache response (2h TTL)
    │
    ▼
Formatted HTML string
    │
    ├── [dry-run] Print to console, strip HTML tags
    ├── [send] formatter.split_message() at 4096 chars
    │       ▼
    │   TelegramDelivery.send_digest_sync()
    │       │── For each recipient chat_id
    │       │── For each message chunk
    │       │── Send with retry (3x, exponential backoff)
    │
    ▼
History logged to logs/digest_history.json
Snapshot saved to logs/retrace/YYYY-MM-DD.json (daytrade only)
```

### Caching Architecture

```
Request → CacheManager.get(key)
              │
              ├── Memory cache hit + fresh? → return
              ├── File cache hit + fresh? → promote to memory, return
              │
              ▼
         Fetch from API
              │
              ├── Success → sanitize NaN/Inf → save to memory + file → return
              ├── Failure → return stale cache (memory or file) if exists
              └── Total failure → return None
```

- Memory cache: Python dict, lost on restart
- File cache: JSON files under `cache/` directory, survives restart
- TTL: per-fetcher (yfinance=2min, others vary)
- NaN handling: `_clean_float()` converts NaN/Inf to None before JSON serialization

### LLM Provider Chain

```
llm_providers.py: LLMProviderChain
    │
    ├── providers list (ordered by config/prompts.yaml provider_priority)
    │       ├── AnthropicProvider (claude-haiku-4-5-20251001)
    │       ├── OpenAIProvider (gpt-4o-mini)
    │       └── GeminiProvider (gemini-2.0-flash)
    │
    ├── Each provider: lazy client init (only if API key present)
    │
    └── call(system_prompt, user_prompt, max_tokens)
            │── Try provider[0] → success? return
            │── Try provider[1] → success? return
            │── Try provider[2] → success? return
            └── All failed → return None (section shows "unavailable")
```

### Multi-Timeframe Scoring Architecture

```
                        ┌─────────────────┐
                        │  Daily OHLCV    │
                        │  (yfinance)     │
                        └────────┬────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                   │
              ▼                  ▼                   ▼
    full_analysis(df)   weekly_full_analysis(df)  monthly_full_analysis(df)
    (daily bars)        (weekly resample)         (monthly resample, needs 2y)
              │                  │                   │
              ▼                  ▼                   ▼
    score_instrument()  score_instrument_swing()  score_instrument_longterm()
    6 factors:          4 factors:               4-5 factors:
    RSI 20%             RSI 25%                  Equity: RSI 10%, Trend 15%,
    Trend 15%           Trend 30%                  Pivot 10%, ATR 5%,
    Pivot 20%           Pivot 25%                  Fundamentals 60%
    ATR 20%             ATR 20%                  Non-equity: RSI 25%,
    Volume 15%                                     Trend 35%, Pivot 25%,
    Gap 10%                                        ATR 15%
              │                  │                   │
              ▼                  ▼                   ▼
    Grade A+ to F       Grade A+ to F            Grade A+ to F
    Entry/Target/Stop   Entry/Target/Stop        Entry/Target/Stop
    (daily pivots/ATR)  (weekly pivots/ATR)      (monthly pivots/ATR)
```

**Fundamentals scoring** (equities only, 6h cache):
- Valuation: P/E, P/B, EV/EBITDA thresholds
- Profitability: gross/operating/net margins, ROE, ROA
- Growth: revenue growth, EPS growth
- Health: D/E ratio, current ratio, free cash flow
- Composite: equal-weight average of 4 sub-scores

### Retrace System

```
Daytrade Digest Run
    │
    ▼
save_snapshot() → logs/retrace/YYYY-MM-DD.json
    │   Contains: date, scoring_weights, prompts_version,
    │   top_picks (with entry/target/stop), prices, sentiment
    │
    ▼ (next trading day or later)
grade_snapshot()
    │── For each pick:
    │       fetch next-day OHLCV via yfinance
    │       hit_target? (high >= target)
    │       hit_stop? (low <= stop)
    │       MFE = high - entry
    │       MAE = entry - low
    │       R-multiple = actual_return / risk
    │       outcome: win | loss | scratch | ambiguous
    │
    ▼
aggregate_performance()
    │── win_rate, avg_r_multiple
    │── by_signal breakdown (RSI bounce, Trend bullish, etc.)
    │── by_trend breakdown (bullish, bearish, neutral)
    │── best/worst picks, daily timeline

Config Versioning:
    save_version() → logs/retrace/versions/{scoring,prompts}/TIMESTAMP.yaml
    diff_versions() → flat key comparison
    rollback() → save current as "Rollback to X", write old content back
```

---

## File Reference

### `config/` — Configuration
```
config/
├── settings.py          # Dataclass: Settings(telegram, api keys, timezone, log_level)
│                        #   get_settings(), reload_settings(), update_env_var()
│                        #   save_instruments(), get_all_yfinance_tickers()
├── instruments.yaml     # 84 instruments: symbol, yfinance, twelvedata, name, category, enabled
├── prompts.yaml         # system_prompt, 25 sections: {name: {prompt, max_tokens}}, provider_priority
├── digests.yaml         # morning/afternoon/weekly/daytrade: sections, default_mode, schedule
└── scoring.yaml         # weights: daytrade (6 keys), swing_weights (4),
                         #   longterm_weights_equity (5 incl. fundamentals=0.60),
                         #   longterm_weights_non_equity (4). Each set sums to 1.0.
```

### `src/analysis/` — Analysis Engine
```
analysis/
├── technicals.py        # full_analysis(hist) → {rsi, sma20, sma50, pivots, trend, atr, ...}
│                        #   weekly_full_analysis(df) → weekly RSI, trend (SMA10w/20w), weekly S/R
│                        #   monthly_full_analysis(df) → monthly RSI, trend (SMA6m/12m), monthly S/R
│                        #   compute_monthly_pivots(df), compute_monthly_atr(df)
├── daytrade_scorer.py   # score_instrument(ta, price) → {symbol, score, entry, target, stop, signals}
├── multi_tf_scorer.py   # score_instrument_swing(ta_weekly, price) → swing score (4 factors)
│                        #   score_instrument_longterm(ta_monthly, price, fundamentals) → LT score
│                        #   Equity: 60% fundamentals + 40% technicals. Non-equity: 100% technicals.
├── fundamentals.py      # fetch_fundamentals(symbol, yf_symbol) → metrics + highlights (6h cache)
│                        #   score_fundamentals(data) → {valuation, profitability, growth, health, composite}
│                        #   is_equity_symbol(category) → True for "us_stock" only
├── indicator_analysis.py# generate_indicator_analyses(ta, scored, price, sym) → human-readable analysis
├── sentiment.py         # compute_composite_sentiment() → {composite_score, classification, components}
├── performance.py       # compute_performance(), rank_instruments(), sector_comparison()
├── llm_analyzer.py      # MarketAnalyzer: analyze_section(name, data, context) → str
│                        #   25 sections incl. multi_tf_outlook, fundamentals_analysis
│                        #   _format_multi_tf_data(), _format_fundamentals_data() formatters
├── llm_providers.py     # LLMProviderChain: call(system, user, max_tokens) → str
├── session_tracker.py   # get_session_performance(hist, session) → {open, high, low, close, change}
└── events.py            # FOMC_DATES, BELLWETHER_TICKERS, get_event_context()
```

### `src/digest/` — Digest Templates
```
digest/
├── builder.py           # DigestBuilder: fetch_prices(), fetch_forex(), run_technicals(), ...
├── formatter.py         # bold(), code(), esc(), section_header(), split_message()
├── morning.py           # build_morning_digest(builder, mode, out_data)
├── afternoon.py         # build_afternoon_digest(builder, mode, out_data)
├── weekly.py            # build_weekly_digest(builder, mode, out_data)
├── daytrade.py          # build_daytrade_digest(builder, mode, out_data) — saves retrace snapshot
└── action_items.py      # build_action_items(builder, digest_type, mode, data)
```

### `src/fetchers/` — Data Sources
```
fetchers/
├── base.py              # BaseFetcher: fetch_with_cache(), _rate_limit_wait(), _stale_fallback()
├── yfinance_fetcher.py  # YFinanceFetcher: get_current_price(), get_history() — TTL: 2min
├── twelvedata_fetcher.py# TwelveDataFetcher: get_forex_rate(), get_intraday() — needs API key
├── finnhub_fetcher.py   # FinnhubFetcher: get_news(), get_earnings() — needs API key
├── fred_fetcher.py      # FREDFetcher: get_series() — needs API key
├── newsapi_fetcher.py   # NewsAPIFetcher: get_headlines() — needs API key
└── feargreed_fetcher.py # FearGreedFetcher: get_index() — no key needed
```

### `src/retrace/` — Performance Tracking
```
retrace/
├── snapshot.py          # save_snapshot(), load_snapshot(), list_snapshots()
├── grader.py            # grade_snapshot(), grade_single_pick(), aggregate_performance()
├── scoring_config.py    # load_scoring_weights(), save_scoring_weights(), validate_weights()
│                        #   load_swing_weights(), load_longterm_weights(is_equity)
├── optimizer.py         # Optimizes scoring weights based on historical performance
├── backfill.py          # Historical snapshot backfilling
└── versioning.py        # save_version(), list_versions(), diff_versions(), rollback()
```

### `ui/routes/` — API Endpoints
```
routes/
├── status.py            # GET /api/status — health check, API configs, cache stats
├── onboarding.py        # GET/PUT /api/onboarding — setup wizard steps
├── settings.py          # GET/PUT /api/settings, export/import, recipients, telegram test
├── instruments.py       # GET /api/instruments, POST toggle, POST create
├── prompts.py           # GET/PUT /api/prompts, system prompt, sections, LLM config
├── digests.py           # GET/PUT /api/digests/config, POST run, POST send
├── sources.py           # GET /api/sources, POST test, POST toggle
├── cache.py             # GET /api/cache/stats, POST /api/cache/clear
├── history.py           # GET /api/history
├── scorecard.py         # GET /all (multi-TF overview) + GET /{symbol} (detail: 2y data, fundamentals)
└── retrace.py           # 16 endpoints: snapshots, grading, scoring, versions, diff, rollback
```

### `ui/frontend/src/pages/` — React Pages
```
pages/
├── Dashboard.tsx        # API health, cache stats, quick run buttons, recent history
├── Onboarding.tsx       # Setup wizard: API keys, Telegram config
├── Instruments.tsx      # Instrument management (toggle, add, grouped by category)
├── Prompts.tsx          # LLM prompt editor, provider priority, model selection
├── DataSources.tsx      # Data source toggles + test buttons
├── DigestConfig.tsx     # Digest section config, mode, schedule
├── RunPreview.tsx       # Run digest, preview (HTML/raw), send to Telegram
├── ScoreCard.tsx        # Multi-TF scorecard grid with DT/SW/LT grade pills + ticker search
├── Settings.tsx         # Timezone, log level, recipients, export/import
└── Retrace.tsx          # 4 tabs: Performance, Scoring, Versions, Audit Trail
```

---

## Extension Points

### Adding a New Digest Type
1. Create `src/digest/newtype.py` with `build_newtype_digest(builder, mode, out_data)` function
2. Add entry to `scripts/run_digest.py` `DIGEST_BUILDERS` dict
3. Add entry to `ui/routes/digests.py` builders dict and validation list
4. Add section config to `config/digests.yaml`
5. Add relevant LLM prompt sections to `config/prompts.yaml` and hardcoded defaults in `llm_analyzer.py`

### Adding a New Data Fetcher
1. Create `src/fetchers/newfetcher.py` extending `BaseFetcher`
2. Implement `get_current_price()` or custom fetch methods
3. Set `api_name` and `cache_ttl` properties
4. Initialize in `src/digest/builder.py` constructor
5. Add API key to `.env.example` and `config/settings.py`
6. Add to `ui/routes/sources.py` for UI toggling

### Adding a New Instrument
1. Add entry to `config/instruments.yaml` with: symbol, yfinance ticker, name, category, enabled
2. Or use the UI: Instruments page -> Add Custom Instrument
3. Instrument appears automatically in all relevant digests

### Adding a New UI Page
1. Create `ui/frontend/src/pages/NewPage.tsx`
2. Add route in `ui/frontend/src/App.tsx`
3. Add nav item in `ui/frontend/src/components/layout/Sidebar.tsx` (and `BottomNav.tsx` for mobile)
4. Create corresponding backend routes in `ui/routes/newroute.py`
5. Register router in `ui/server.py`

---

## Common Code Patterns

### Fetcher Pattern (BaseFetcher)
```python
class YFinanceFetcher(BaseFetcher):
    @property
    def api_name(self) -> str:
        return "yfinance"

    @property
    def cache_ttl(self) -> int:
        return 120  # 2 minutes

    def get_current_price(self, ticker: str) -> dict[str, Any] | None:
        def _fetch():
            t = yf.Ticker(ticker)
            # ... fetch and clean data
            return result
        return self.fetch_with_cache(f"price:{ticker}", _fetch)
```

### Digest Builder Pattern
```python
def build_daytrade_digest(builder: DigestBuilder, mode: str = "facts", out_data: dict | None = None) -> str:
    parts = []
    digest_data = {}

    # 1. Fetch data
    prices = builder.fetch_daytrade_universe()

    # 2. Run analysis
    for t in all_tickers:
        ta = full_analysis(hist, ticker=sym)
        result = score_instrument(ta, prices[sym])

    # 3. Format sections (add LLM if mode=full)
    if analyzer:
        summary = analyzer.analyze_section("daytrade_summary", digest_data)

    # 4. Save retrace snapshot
    save_snapshot(digest_data, load_scoring_weights(), ...)

    return "\n".join(parts)
```

### API Route Pattern (FastAPI)
```python
router = APIRouter(prefix="/api/retrace", tags=["retrace"])

@router.get("/snapshots")
def get_snapshots(limit: int = Query(30, ge=1, le=200)):
    return list_snapshots(limit=limit)

@router.put("/scoring")
def update_scoring(body: ScoringWeightsUpdate):
    ok, msg = validate_weights(body.weights)
    if not ok:
        raise HTTPException(400, msg)
    save_scoring_weights(body.weights, body.description)
    return {"success": True, "weights": body.weights}
```

### Frontend Page Pattern (React + useApi)
```tsx
export default function Retrace() {
  const { data, loading, refetch } = useApi<DataType>('/retrace/endpoint')
  const { toasts, addToast, removeToast } = useToast()

  if (loading) return <LoadingSpinner />

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto pb-24 md:pb-6">
      {/* Page content with Tailwind + Apple design system */}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
```

---

## Environment Variables

```bash
# Required
TELEGRAM_BOT_TOKEN=          # Telegram bot token for delivery
TELEGRAM_CHAT_ID=            # Primary recipient chat ID

# Data APIs (optional — yfinance is free with no key)
TWELVEDATA_API_KEY=          # Real-time forex (800 calls/day free)
FINNHUB_API_KEY=             # Company news (60 calls/min free)
FRED_API_KEY=                # Federal Reserve data (free)
NEWSAPI_KEY=                 # News headlines (100 calls/day free)

# LLM Providers (at least one for mode=full)
ANTHROPIC_API_KEY=           # Claude (primary)
OPENAI_API_KEY=              # GPT-4o-mini (fallback 1)
GEMINI_API_KEY=              # Gemini 2.0 Flash (fallback 2)

# Optional overrides
TIMEZONE=US/Central          # Default timezone
LOG_LEVEL=INFO               # DEBUG, INFO, WARNING, ERROR
```

---

## Instruments Configuration

Instruments are defined in `config/instruments.yaml` with these fields:
```yaml
- symbol: EURUSD        # Display symbol
  yfinance: EURUSD=X    # yfinance ticker
  twelvedata: EUR/USD    # TwelveData ticker (optional)
  name: Euro/Dollar
  category: forex
  subcategory: major
  enabled: true          # Toggle visibility
```

Categories: `forex` (7), `us_index` (4), `futures` (3), `commodities` (14), `crypto` (5), `us_stock` (46), `fred_series` (8), `session` (4)

Total: 84 instruments (78 enabled)

---

## Digest Schedules (macOS launchd)

| Digest | Schedule | Plist |
|--------|----------|-------|
| Morning | Mon-Fri 6:30 AM CT | `com.market-digest.morning.plist` |
| Afternoon | Mon-Fri 4:30 PM CT | `com.market-digest.afternoon.plist` |
| Weekly | Friday 5:30 PM CT | `com.market-digest.weekly.plist` |
| Day Trade | Mon-Fri 8:15 AM CT | `com.market-digest.daytrade.plist` |

---

*Last updated: 2026-02-14*
*Maintained by: Development Team & AI Agents*
