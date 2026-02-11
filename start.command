#!/bin/bash
# ──────────────────────────────────────────────────────────
# Market Digest — Command Center
# Double-click this file to launch the web UI.
# ──────────────────────────────────────────────────────────

cd "$(dirname "$0")"

clear
echo "╔══════════════════════════════════════════════════╗"
echo "║        Market Digest — Command Center            ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── Find Python ─────────────────────────────────────────

VENV_PY="$(pwd)/.venv/bin/python3"

if [ ! -f "$VENV_PY" ]; then
    echo "⚠  Virtual environment not found. Creating one..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo ""
        echo "❌  Could not create virtual environment."
        echo "    Install Python 3.12+: https://www.python.org/downloads/"
        echo ""
        echo "Press Enter to close."
        read
        exit 1
    fi
    echo "   Installing Python packages (one-time setup)..."
    "$VENV_PY" -m pip install -q -r requirements.txt
    echo "   Done."
    echo ""
fi

# ── Check Python deps ──────────────────────────────────

"$VENV_PY" -c "import fastapi, uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦  Installing missing Python packages..."
    "$VENV_PY" -m pip install -q fastapi uvicorn python-multipart
fi

# ── Build frontend if needed ───────────────────────────

if [ ! -d "ui/frontend/dist" ]; then
    if command -v node &>/dev/null; then
        echo "🔨  Building web interface (first launch only)..."
        cd ui/frontend
        [ ! -d "node_modules" ] && npm install --silent
        npm run build --silent
        cd ../..
        echo "   Done."
        echo ""
    else
        echo "⚠  Node.js not found — frontend cannot build."
        echo "   Install Node.js from https://nodejs.org"
        echo "   Then re-launch this file."
        echo ""
        echo "Press Enter to close."
        read
        exit 1
    fi
fi

# ── Launch ─────────────────────────────────────────────

PORT=8550
URL="http://localhost:$PORT"

echo "🚀  Starting server at $URL"

# Detect LAN IP for phone access
LAN_IP=$(ipconfig getifaddr en0 2>/dev/null)
if [ -n "$LAN_IP" ]; then
    echo "📱  Phone access: http://$LAN_IP:$PORT"
fi

echo "    Your browser will open automatically."
echo ""
echo "    To stop: close this window or press Ctrl+C."
echo "────────────────────────────────────────────────────"
echo ""

# Open browser after a short delay
(sleep 2 && open "$URL") &

# Start the server
"$VENV_PY" -m uvicorn ui.server:app --host 0.0.0.0 --port $PORT --log-level warning

echo ""
echo "Server stopped. You can close this window."
read
