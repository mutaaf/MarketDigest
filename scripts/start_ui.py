#!/usr/bin/env python3
"""One-command launcher: builds frontend if needed, starts uvicorn, opens browser.

Usage:
    python scripts/start_ui.py          # works from any Python
    .venv/bin/python scripts/start_ui.py # explicit venv
"""

import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "ui" / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python3"

PORT = 8550


# ── Auto-relaunch inside venv if we're not already there ────────

def _in_venv() -> bool:
    return sys.prefix != sys.base_prefix


def _ensure_venv():
    """If not running inside the project venv, re-exec ourselves with it."""
    if _in_venv():
        return  # already inside a venv

    if not VENV_PYTHON.exists():
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(PROJECT_ROOT / ".venv")], check=True)
        print("Installing project dependencies...")
        subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "-q", "-r", str(PROJECT_ROOT / "requirements.txt")], check=True)

    # Re-exec with the venv Python
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), __file__] + sys.argv[1:])


# ── Helpers ──────────────────────────────────────────────────────

def _check_node() -> bool:
    try:
        return subprocess.run(["node", "--version"], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


def _install_frontend_deps():
    if not (FRONTEND_DIR / "node_modules").exists():
        print("Installing frontend dependencies...")
        subprocess.run(["npm", "install"], cwd=str(FRONTEND_DIR), check=True)


def _build_frontend():
    if DIST_DIR.exists():
        src_dir = FRONTEND_DIR / "src"
        if src_dir.exists():
            src_mtime = max(f.stat().st_mtime for f in src_dir.rglob("*") if f.is_file())
            dist_mtime = max((f.stat().st_mtime for f in DIST_DIR.rglob("*") if f.is_file()), default=0)
            if dist_mtime >= src_mtime:
                print("Frontend build is up to date.")
                return

    print("Building frontend...")
    subprocess.run(["npm", "run", "build"], cwd=str(FRONTEND_DIR), check=True)
    print("Frontend built successfully.")


def _check_python_deps():
    try:
        import fastapi  # noqa
        import uvicorn   # noqa
    except ImportError:
        print("Installing server dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                        "fastapi>=0.115.0", "uvicorn[standard]>=0.32.0", "python-multipart>=0.0.9"],
                       check=True)


# ── Main ─────────────────────────────────────────────────────────

def main():
    _ensure_venv()

    # Now we're guaranteed to be inside the venv
    sys.path.insert(0, str(PROJECT_ROOT))
    os.chdir(str(PROJECT_ROOT))

    print()
    print("  Market Digest — Command Center")
    print("  " + "─" * 40)
    print()

    _check_python_deps()

    if _check_node():
        _install_frontend_deps()
        _build_frontend()
    elif not DIST_DIR.exists():
        print("\n  WARNING: Node.js not found and no frontend build exists.")
        print("  Install Node.js (https://nodejs.org) then re-run.\n")
        sys.exit(1)

    url = f"http://localhost:{PORT}"
    print(f"\n  Server starting at {url}")

    # Detect LAN IP for phone access
    try:
        lan_ip = socket.gethostbyname(socket.gethostname())
        if lan_ip and not lan_ip.startswith("127."):
            print(f"  Phone access:   http://{lan_ip}:{PORT}")
    except Exception:
        pass

    print("  Press Ctrl+C to stop.\n")

    import threading
    threading.Thread(target=lambda: (time.sleep(1.5), webbrowser.open(url)), daemon=True).start()

    import uvicorn
    uvicorn.run("ui.server:app", host="0.0.0.0", port=PORT, reload=False, log_level="warning")


if __name__ == "__main__":
    main()
