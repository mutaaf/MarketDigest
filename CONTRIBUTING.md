# Contributing to Market Digest

Thanks for your interest in contributing! This guide covers development setup, code conventions, and how to extend the system.

## Development Setup

### Backend

```bash
# Clone and set up
git clone https://github.com/YOUR_USERNAME/market-digest.git
cd market-digest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with at least your Telegram credentials (or use --dry-run)
```

### Frontend (hot reload)

```bash
cd ui/frontend
npm install
npm run dev          # Vite dev server on port 5173 (proxies API to 8550)
```

In a separate terminal, start the backend:

```bash
.venv/bin/python -m uvicorn ui.server:app --host 0.0.0.0 --port 8550 --reload
```

### Running Tests

```bash
make test            # or: .venv/bin/python -m pytest
make lint            # or: .venv/bin/python -m ruff check .
```

## Code Style

- **Python**: Ruff for linting, 120 char line length, Python 3.12 target
- **TypeScript/React**: Standard ESLint + Prettier via Vite defaults
- **No database** — all persistence is YAML configs + JSON files
- **Keep it simple** — this project values clarity over abstraction

## How To...

### Add a New Data Fetcher

1. Create `src/fetchers/your_source.py` with a fetch function
2. Add it to the builder in `src/digest/builder.py`
3. Add any required API keys to `.env.example` with signup URLs
4. Update `scripts/test_apis.py` to include a connection test

### Add a New Digest Section

1. Add the section template to `config/prompts.yaml`
2. Add formatting logic in `src/digest/formatter.py`
3. Wire it into the appropriate digest builder (`morning.py`, `afternoon.py`, etc.)

### Add a New Scoring Dimension

1. Add weight key to `config/scoring.yaml` (all weights must sum to 1.0)
2. Implement the scoring function in `src/analysis/daytrade_scorer.py` (or `multi_tf_scorer.py`)
3. Update the UI weight editor if needed (`ui/frontend/src/pages/Weights.tsx`)

### Add a New API Endpoint

1. Create or edit a route file in `ui/routes/`
2. Register it in `ui/server.py`
3. Add Pydantic models to `ui/models.py` if needed

## Pull Requests

1. Fork the repo and create a feature branch
2. Make your changes with clear commit messages
3. Run `make lint` and `make test` before submitting
4. Open a PR with a brief description of what and why

## Reporting Issues

Open a GitHub issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your OS and Python version
