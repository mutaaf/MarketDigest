#!/bin/bash
# launchd entrypoint for the always-on UI server (location-independent)
cd "$(dirname "$0")/.." || exit 1
exec .venv/bin/python -m uvicorn ui.server:app --host 0.0.0.0 --port 8550 --log-level warning
