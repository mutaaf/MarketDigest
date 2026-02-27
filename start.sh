#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Market Digest — Command Center Launcher
# Works on macOS and Linux. (macOS users can also use start.command)
# ──────────────────────────────────────────────────────────────

cd "$(dirname "$0")"

clear
echo "╔══════════════════════════════════════════════════╗"
echo "║        Market Digest — Command Center            ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── Find Python ──────────────────────────────────────────────

VENV_PY="$(pwd)/.venv/bin/python3"

if [ ! -f "$VENV_PY" ]; then
    echo "  Virtual environment not found. Run setup first:"
    echo "    ./setup.sh"
    echo ""
    echo "Press Enter to close."
    read
    exit 1
fi

# ── Check Python deps ───────────────────────────────────────

"$VENV_PY" -c "import fastapi, uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "  Installing missing Python packages..."
    "$VENV_PY" -m pip install -q fastapi uvicorn python-multipart
fi

# ── Build frontend if needed ────────────────────────────────

if [ ! -d "ui/frontend/dist" ]; then
    if command -v node &>/dev/null; then
        echo "  Building web interface (first launch only)..."
        cd ui/frontend
        [ ! -d "node_modules" ] && npm install --silent
        npm run build --silent
        cd ../..
        echo "  Done."
        echo ""
    else
        echo "  Node.js not found — frontend cannot build."
        echo "  Install Node.js from https://nodejs.org"
        echo "  Then re-launch this script."
        echo ""
        echo "Press Enter to close."
        read
        exit 1
    fi
fi

# ── Launch ───────────────────────────────────────────────────

PORT=8550
URL="http://localhost:$PORT"

echo "  Starting server at $URL"

# Detect LAN IP (cross-platform)
LAN_IP=""
if command -v ipconfig &>/dev/null && [[ "$(uname)" == "Darwin" ]]; then
    # macOS
    LAN_IP=$(ipconfig getifaddr en0 2>/dev/null)
elif command -v hostname &>/dev/null; then
    # Linux
    LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
fi

if [ -n "$LAN_IP" ]; then
    echo "  Phone access: http://$LAN_IP:$PORT"
fi

echo "  Your browser will open automatically."
echo ""
echo "  To stop: close this window or press Ctrl+C."
echo "────────────────────────────────────────────────────"
echo ""

# Open browser (cross-platform)
open_browser() {
    sleep 2
    if command -v open &>/dev/null; then
        open "$URL"          # macOS
    elif command -v xdg-open &>/dev/null; then
        xdg-open "$URL"     # Linux
    elif command -v wslview &>/dev/null; then
        wslview "$URL"      # WSL
    fi
}
open_browser &

# ── Auto-restart loop ────────────────────────────────────────
# Restarts on crash with exponential backoff (2s → 4s → 8s → … → 60s).
# Resets backoff after 30s of healthy uptime.
# Ctrl+C (SIGINT) exits cleanly without restart.

BACKOFF=2
MAX_BACKOFF=60
STOPPED_BY_USER=0

trap 'STOPPED_BY_USER=1' INT TERM

while true; do
    START_TIME=$(date +%s)

    "$VENV_PY" -m uvicorn ui.server:app --host 0.0.0.0 --port $PORT --log-level warning &
    SERVER_PID=$!
    wait $SERVER_PID
    EXIT_CODE=$?

    if [ "$STOPPED_BY_USER" -eq 1 ]; then
        echo ""
        echo "Server stopped by user."
        exit 0
    fi

    END_TIME=$(date +%s)
    UPTIME=$((END_TIME - START_TIME))

    # Reset backoff if server ran for >30s (was healthy)
    if [ "$UPTIME" -gt 30 ]; then
        BACKOFF=2
    fi

    echo ""
    echo "  Server exited (code $EXIT_CODE, uptime ${UPTIME}s). Restarting in ${BACKOFF}s..."
    sleep $BACKOFF

    # Exponential backoff, capped
    BACKOFF=$((BACKOFF * 2))
    if [ "$BACKOFF" -gt "$MAX_BACKOFF" ]; then
        BACKOFF=$MAX_BACKOFF
    fi
done
