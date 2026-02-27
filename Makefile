.PHONY: setup ui dev build digest-dry test lint clean docker-up docker-down test-apis schedule-install help

PYTHON = .venv/bin/python
PIP = .venv/bin/pip

help: ## Show this help
	@echo ""
	@echo "  Market Digest — Available Commands"
	@echo "  ───────────────────────────────────────────────"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'
	@echo ""

setup: ## Full setup (venv, deps, frontend build)
	@./setup.sh

ui: ## Start the web UI
	$(PYTHON) scripts/start_ui.py

dev: ## Start backend with hot-reload (for development)
	$(PYTHON) -m uvicorn ui.server:app --host 0.0.0.0 --port 8550 --reload

build: ## Build the frontend
	cd ui/frontend && npm run build

digest-dry: ## Run a dry-run daytrade digest (no API keys needed)
	$(PYTHON) scripts/run_digest.py --type daytrade --mode facts --dry-run

test: ## Run tests
	$(PYTHON) -m pytest tests/ -v

lint: ## Run linter
	$(PYTHON) -m ruff check .

clean: ## Remove build artifacts and cache
	rm -rf ui/frontend/dist ui/frontend/node_modules/.cache
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	rm -rf cache/*.json
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

docker-up: ## Build and start with Docker
	docker compose up --build

docker-down: ## Stop Docker containers
	docker compose down

test-apis: ## Test API connections
	$(PYTHON) scripts/test_apis.py

schedule-install: ## Install macOS launchd schedule
	$(PYTHON) scripts/setup_launchd.py
