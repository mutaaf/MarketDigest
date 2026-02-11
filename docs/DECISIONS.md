# Architecture Decision Records

This document captures key decisions made during development, their context, and rationale.

---

## ADR-001: File-Based Persistence (No Database)

### Status
Accepted

### Context
The project needs to persist configuration (instruments, prompts, digest config), cache data, and run history. A traditional database (SQLite, PostgreSQL) was considered.

### Decision
Use YAML files for config, JSON files for cache and logs. No database.

### Rationale
1. Single-user local application — no concurrent write concerns
2. YAML configs are human-readable and editable outside the UI
3. JSON cache files are self-contained and trivially portable
4. Zero setup — no database server, migrations, or ORM
5. Config files can be version-controlled or backed up as a zip

### Implementation
- `config/*.yaml` — instruments, prompts, digests, scoring weights
- `cache/*.json` — per-fetcher cached responses with TTL metadata
- `logs/digest_history.json` — run history (last 100 entries)
- `logs/retrace/*.json` — per-date snapshots

### Consequences
- Positive: Zero dependencies, instant setup, portable
- Negative: No concurrent write safety, no query capability, manual cleanup of cache files
- Mitigation: Atomic writes (write to .tmp then rename) for critical files

---

## ADR-002: Multi-Provider LLM Fallback Chain

### Status
Accepted

### Context
LLM analysis enhances digests with market commentary, but no single provider guarantees 100% availability. Different users may have different API keys.

### Decision
Implement a 3-provider fallback chain: Anthropic Claude -> OpenAI GPT-4o-mini -> Google Gemini 2.0 Flash. Use whichever key is available, in priority order.

### Rationale
1. Maximizes uptime — if one provider is down, next is tried automatically
2. Users only need one key — not locked to any provider
3. Fast, cheap models preferred (Haiku, 4o-mini, Flash) since analysis is summaries not complex reasoning
4. Lazy client initialization — only SDK for available keys is loaded

### Implementation
- `src/analysis/llm_providers.py` — `LLMProviderChain` with ordered provider list
- `config/prompts.yaml` — `provider_priority` and `provider_models` are user-configurable
- Each section call tries providers in order until one succeeds
- 2-hour response cache to reduce API calls

### Consequences
- Positive: High availability, user flexibility, cost optimization
- Negative: Slight inconsistency in output style between providers
- Mitigation: Strong system prompt and section prompts normalize output style

---

## ADR-003: Dual-Tier Caching (Memory + File)

### Status
Accepted

### Context
Market data fetching involves rate-limited external APIs. The same data is often needed multiple times within a single digest build (e.g., prices used in scoring, ranking, and formatting).

### Decision
Implement two-tier cache: in-memory Python dict (fast, lost on restart) + file-backed JSON (slower, persists across restarts). TTL-based expiry per fetcher. Stale fallback on fetch failure.

### Rationale
1. Memory tier eliminates redundant API calls within a single run
2. File tier preserves data across process restarts (useful for scheduled runs)
3. Stale fallback prevents digest failures when APIs are temporarily unavailable
4. NaN/Infinity sanitization required because market data can contain these values

### Implementation
- `src/cache/manager.py` — `CacheManager` with `get()`, `set()`, `get_stale()`
- Cache key format: `{api_name}:{method}:{params}`
- File storage: `cache/{key_hash}.json`
- TTL: per-fetcher (yfinance=2min, TwelveData=5min, etc.)

### Consequences
- Positive: Fast, resilient, no external dependencies
- Positive: Market data stays available even during API outages
- Negative: Cache directory grows over time (hundreds of files)
- Mitigation: Cache clear available via UI and API

---

## ADR-004: YAML-Backed LLM Prompts with Hardcoded Fallbacks

### Status
Accepted

### Context
LLM prompts need to be editable by the user (via web UI) but must work out of the box without any configuration.

### Decision
Prompts are stored in `config/prompts.yaml` but `llm_analyzer.py` contains hardcoded defaults for all 18 section types. YAML values override defaults when present.

### Rationale
1. Works immediately on first run — no setup needed
2. Users can customize any prompt via the web UI
3. Reset-to-default is trivial (delete the section from YAML)
4. Hardcoded defaults serve as documentation of expected prompt structure

### Implementation
- `src/analysis/llm_analyzer.py` — `_DEFAULT_PROMPTS` dict with all 18 sections
- `config/prompts.yaml` — user overrides (only customized sections present)
- `ui/routes/prompts.py` — CRUD endpoints that merge YAML with defaults
- `reload_prompts()` — called after every save to refresh in-memory prompts

### Consequences
- Positive: Zero-config startup, easy customization, easy reset
- Negative: Prompt changes require understanding both YAML and Python defaults
- Mitigation: UI shows current effective prompt (merged) with "is_default" flag

---

## ADR-005: Telegram as Primary Delivery Channel

### Status
Accepted

### Context
Digests need to be delivered to the user in a timely, mobile-friendly format. Options considered: email, Slack, Discord, SMS, Telegram, web push notifications.

### Decision
Use Telegram as the sole delivery channel.

### Rationale
1. Free bot API with generous rate limits
2. Rich HTML formatting (bold, italic, code blocks)
3. Mobile-first — instant push notifications
4. Multi-recipient support via chat IDs
5. No authentication complexity (just bot token + chat ID)
6. Messages are searchable and persistent in chat history

### Implementation
- `src/delivery/telegram_bot.py` — `TelegramDelivery` class
- Auto-splits messages at 4096 char limit (Telegram API constraint)
- Split points chosen at section headers for readability
- Retry: 3 attempts, exponential backoff 3-30s
- Multi-recipient: sends to all configured chat IDs with 1s pause

### Consequences
- Positive: Free, reliable, mobile-friendly, rich formatting
- Negative: 4096 char limit requires message splitting logic
- Negative: No built-in charts/images (text only)

---

## ADR-006: Externalized Scoring Weights (Retrace System)

### Status
Accepted

### Context
Day trade scoring used hardcoded weights in `daytrade_scorer.py`. There was no way to tune weights based on actual performance or to track which weight configurations produced better results.

### Decision
Externalize scoring weights to `config/scoring.yaml`, add version tracking, and build a grading system that compares picks against actual next-day prices.

### Rationale
1. Weights can be tuned via UI without code changes
2. Version history enables A/B comparison of weight configurations
3. Grading against actual prices provides objective performance measurement
4. Audit trail connects weight/prompt changes to performance changes

### Implementation
- `config/scoring.yaml` — weights externalized (6 keys summing to 1.0)
- `src/retrace/scoring_config.py` — load/save/validate with sum=1.0 constraint
- `src/retrace/snapshot.py` — captures picks + weights + prices per run
- `src/retrace/grader.py` — grades picks against next-day OHLCV
- `src/retrace/versioning.py` — tracks all config changes with diff + rollback
- `ui/routes/retrace.py` — 12 API endpoints
- `ui/frontend/src/pages/Retrace.tsx` — 4-tab UI (Performance, Scoring, Versions, Audit Trail)

### Consequences
- Positive: Data-driven tuning workflow, full audit trail
- Positive: Rollback capability prevents losing a known-good configuration
- Negative: Grading requires next trading day to pass (not instant)
- Negative: Intraday order ambiguity when both target and stop are hit same day

---

## ADR-007: React + Vite + Tailwind for Frontend

### Status
Accepted

### Context
The project needed a web UI for configuration management, digest preview, and performance tracking. Framework choice needed to balance development speed, bundle size, and maintainability.

### Decision
Use React 18 + Vite + TypeScript + Tailwind CSS with an Apple-inspired design system.

### Rationale
1. React — mature ecosystem, wide AI assistant support
2. Vite — fast builds (<4s), excellent HMR for development
3. TypeScript — type safety for API contracts
4. Tailwind — utility-first, consistent styling without custom CSS files
5. No state management library — `useState` + `useApi` hook sufficient for this scale
6. Single-page app served as static files by FastAPI — no separate server needed

### Implementation
- `ui/frontend/` — Vite project with React + TypeScript
- `ui/frontend/src/hooks/useApi.ts` — generic data fetching hook
- `ui/frontend/src/api/client.ts` — axios instance with `/api` base URL
- Built to `ui/frontend/dist/`, served by FastAPI `StaticFiles` mount
- Apple design system: `apple-gray-*`, `apple-blue` color tokens in Tailwind config

### Consequences
- Positive: Fast development, type-safe, consistent styling
- Positive: Single deployment — frontend built into backend's static files
- Negative: No SSR, no SEO (not needed for admin tool)

---

## ADR-008: macOS launchd for Scheduling

### Status
Accepted

### Context
Digests need to run on a schedule (morning 6:30 AM, afternoon 4:30 PM, etc.). Options: cron, systemd, launchd, cloud scheduler, Python scheduler (APScheduler).

### Decision
Use macOS native launchd with plist files.

### Rationale
1. Native to macOS — no additional software needed
2. Survives sleep/wake cycles (runs missed jobs on wake)
3. Stdout/stderr logging built in
4. Simple plist XML format
5. `scripts/setup_launchd.py` automates plist generation and registration

### Implementation
- `scripts/setup_launchd.py` — generates plist files, registers with `launchctl`
- `launchd/com.market-digest.*.plist` — one per digest type
- Logs captured to `logs/{type}_stdout.log` and `logs/{type}_stderr.log`

### Consequences
- Positive: Zero dependencies, reliable, handles sleep/wake
- Negative: macOS only — not portable to Linux/Windows
- Mitigation: CLI entry point (`run_digest.py`) works on any platform; only scheduling is macOS-specific
