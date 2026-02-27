#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Market Digest — Interactive Setup
# Works on macOS and Linux. For Windows, use setup.bat instead.
# ──────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║        Market Digest — Setup                     ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── Colors ────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
info() { echo -e "  ${BLUE}→${NC} $1"; }

# ── Step 1: Check Python ─────────────────────────────────────
echo "Step 1/5: Checking Python..."

PYTHON=""
for cmd in python3.12 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    fail "Python 3.10+ is required but not found."
    echo "    Install Python: https://www.python.org/downloads/"
    exit 1
fi
ok "Found $PYTHON ($($PYTHON --version 2>&1))"

# ── Step 2: Create virtual environment ────────────────────────
echo ""
echo "Step 2/5: Setting up Python virtual environment..."

if [ ! -d ".venv" ]; then
    $PYTHON -m venv .venv
    ok "Created virtual environment (.venv/)"
else
    ok "Virtual environment already exists"
fi

# Activate
source .venv/bin/activate

# Install Python packages
info "Installing Python packages (this may take a minute)..."
pip install -q -r requirements.txt
ok "Python packages installed"

# ── Step 3: Environment file ─────────────────────────────────
echo ""
echo "Step 3/5: Setting up environment file..."

if [ -f ".env" ]; then
    ok ".env file already exists (skipping)"
    SETUP_ENV=false
else
    cp .env.example .env
    ok "Created .env from template"
    SETUP_ENV=true
fi

if [ "$SETUP_ENV" = true ]; then
    echo ""
    echo "  Would you like to enter your API keys now?"
    echo "  (You can always edit .env later)"
    echo ""
    read -p "  Set up API keys interactively? [Y/n] " -r REPLY
    echo ""

    if [[ ! "$REPLY" =~ ^[Nn]$ ]]; then

        # ── Telegram ──
        echo -e "  ${BLUE}── Telegram (for digest delivery) ──${NC}"
        echo "  Create a bot: message @BotFather on Telegram"
        echo ""
        read -p "  Telegram Bot Token (Enter to skip): " TG_TOKEN
        if [ -n "$TG_TOKEN" ]; then
            sed -i.bak "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=$TG_TOKEN|" .env
            read -p "  Telegram Chat ID: " TG_CHAT
            if [ -n "$TG_CHAT" ]; then
                sed -i.bak "s|^TELEGRAM_CHAT_ID=.*|TELEGRAM_CHAT_ID=$TG_CHAT|" .env
            fi
            ok "Telegram configured"
        else
            warn "Skipped Telegram (use --dry-run to preview digests)"
        fi
        echo ""

        # ── Data sources ──
        echo -e "  ${BLUE}── Data Sources (all optional, enhance your digests) ──${NC}"
        echo ""

        read -p "  TwelveData key (https://twelvedata.com, Enter to skip): " TD_KEY
        if [ -n "$TD_KEY" ]; then
            sed -i.bak "s|^# TWELVEDATA_API_KEY=.*|TWELVEDATA_API_KEY=$TD_KEY|" .env
            ok "TwelveData configured"
        fi

        read -p "  Finnhub key (https://finnhub.io, Enter to skip): " FH_KEY
        if [ -n "$FH_KEY" ]; then
            sed -i.bak "s|^# FINNHUB_API_KEY=.*|FINNHUB_API_KEY=$FH_KEY|" .env
            ok "Finnhub configured"
        fi

        read -p "  FRED key (https://fred.stlouisfed.org, Enter to skip): " FRED_KEY
        if [ -n "$FRED_KEY" ]; then
            sed -i.bak "s|^# FRED_API_KEY=.*|FRED_API_KEY=$FRED_KEY|" .env
            ok "FRED configured"
        fi

        read -p "  NewsAPI key (https://newsapi.org, Enter to skip): " NEWS_KEY
        if [ -n "$NEWS_KEY" ]; then
            sed -i.bak "s|^# NEWSAPI_KEY=.*|NEWSAPI_KEY=$NEWS_KEY|" .env
            ok "NewsAPI configured"
        fi
        echo ""

        # ── LLM ──
        echo -e "  ${BLUE}── LLM Provider (optional, adds AI commentary) ──${NC}"
        echo "  Add any ONE key to enable AI analysis in digests."
        echo ""

        read -p "  Anthropic key (https://console.anthropic.com, Enter to skip): " ANTH_KEY
        if [ -n "$ANTH_KEY" ]; then
            sed -i.bak "s|^# ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$ANTH_KEY|" .env
            ok "Anthropic configured"
        fi

        read -p "  OpenAI key (https://platform.openai.com, Enter to skip): " OAI_KEY
        if [ -n "$OAI_KEY" ]; then
            sed -i.bak "s|^# OPENAI_API_KEY=.*|OPENAI_API_KEY=$OAI_KEY|" .env
            ok "OpenAI configured"
        fi

        read -p "  Gemini key (https://aistudio.google.com, Enter to skip): " GEM_KEY
        if [ -n "$GEM_KEY" ]; then
            sed -i.bak "s|^# GEMINI_API_KEY=.*|GEMINI_API_KEY=$GEM_KEY|" .env
            ok "Gemini configured"
        fi

        # Clean up backup files from sed -i
        rm -f .env.bak
    fi
fi

# ── Step 4: Frontend ──────────────────────────────────────────
echo ""
echo "Step 4/5: Building frontend..."

if command -v node &>/dev/null; then
    ok "Found Node.js ($(node --version))"
    cd ui/frontend
    if [ ! -d "node_modules" ]; then
        info "Installing frontend packages..."
        npm install --silent
    fi
    info "Building frontend..."
    npm run build --silent
    cd ../..
    ok "Frontend built"
else
    warn "Node.js not found — skipping frontend build."
    echo "    The web UI won't work until you install Node.js (https://nodejs.org)"
    echo "    and run: cd ui/frontend && npm install && npm run build"
fi

# ── Step 5: Verify ────────────────────────────────────────────
echo ""
echo "Step 5/5: Verifying installation..."

.venv/bin/python -c "
import sys
errors = []
try:
    import yfinance
except ImportError:
    errors.append('yfinance')
try:
    import fastapi
except ImportError:
    errors.append('fastapi')
try:
    import yaml
except ImportError:
    errors.append('pyyaml')

if errors:
    print(f'Missing packages: {errors}')
    sys.exit(1)
print('All core packages OK')
"
ok "Python packages verified"

# Create runtime directories
mkdir -p logs/retrace cache
ok "Runtime directories ready"

# ── Done ──────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════"
echo ""
ok "Setup complete!"
echo ""
echo "  Next steps:"
echo ""
echo "    Start the web UI:"
echo "      .venv/bin/python scripts/start_ui.py"
echo ""
echo "    Run a digest (preview in terminal):"
echo "      .venv/bin/python scripts/run_digest.py --type daytrade --mode facts --dry-run"
echo ""
echo "    Run a digest (send to Telegram):"
echo "      .venv/bin/python scripts/run_digest.py --type morning --mode full"
echo ""
echo "    See all options:"
echo "      make help"
echo ""
