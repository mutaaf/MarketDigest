#!/usr/bin/env python3
"""One-command launcher: builds frontend if needed, starts uvicorn, opens browser.

Self-healing: restarts on crash with exponential backoff, detects port conflicts,
logs crashes. Can install as a macOS launchd service for always-online operation.

Usage:
    python scripts/start_ui.py                # start server (auto-restarts on crash)
    python scripts/start_ui.py --install-service   # install as launchd service
    python scripts/start_ui.py --uninstall-service # remove launchd service
    python scripts/start_ui.py --status            # check service status
"""

import argparse
import os
import signal
import socket
import subprocess
import sys
import time
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "ui" / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python3"
LOGS_DIR = PROJECT_ROOT / "logs"
CRASH_LOG = LOGS_DIR / "ui_server.log"

PORT = 8550

LAUNCHD_LABEL = "com.mutaafaziz.market-digest-ui"
PLIST_SOURCE = PROJECT_ROOT / "launchd" / f"{LAUNCHD_LABEL}.plist"
PLIST_DEST = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"

MAX_RAPID_RESTARTS = 10
RAPID_WINDOW = 60  # seconds


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


# ── Port conflict detection ──────────────────────────────────────

def _kill_stale_port():
    """Detect and kill stale processes holding our port."""
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{PORT}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return  # port is free

        pids = [int(p) for p in result.stdout.strip().split("\n") if p.strip()]
        my_pid = os.getpid()

        for pid in pids:
            if pid == my_pid:
                continue

            # Check if it's a python/uvicorn process (ours) or something else
            try:
                ps_result = subprocess.run(
                    ["ps", "-p", str(pid), "-o", "command="],
                    capture_output=True, text=True, timeout=5,
                )
                cmd = ps_result.stdout.strip()
            except Exception:
                cmd = ""

            is_ours = "start_ui" in cmd or "ui.server" in cmd or "uvicorn" in cmd

            if is_ours:
                print(f"  Killing stale process {pid} on port {PORT}...")
                try:
                    os.kill(pid, signal.SIGTERM)
                    # Wait up to 3s for graceful shutdown
                    for _ in range(30):
                        time.sleep(0.1)
                        try:
                            os.kill(pid, 0)  # check if still alive
                        except ProcessLookupError:
                            break
                    else:
                        # Still alive after 3s, force kill
                        print(f"  Force-killing stale process {pid}...")
                        os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass  # already dead
            else:
                print(f"\n  ERROR: Port {PORT} is held by another program (PID {pid}):")
                print(f"    {cmd}")
                print(f"  Free the port or change PORT in start_ui.py.\n")
                sys.exit(1)

        # Brief pause for port to fully release
        time.sleep(0.5)

    except Exception as e:
        # lsof not available or other issue — proceed and let uvicorn report the error
        _log_crash(e, prefix="Port check warning")


# ── Crash logging ────────────────────────────────────────────────

def _log_crash(exc, prefix="CRASH"):
    """Append a timestamped crash entry to the log file."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    entry = f"[{timestamp}] {prefix}: {exc}\n{''.join(tb)}\n"

    try:
        with open(CRASH_LOG, "a") as f:
            f.write(entry)
    except Exception:
        pass  # don't crash the crash logger

    print(f"\n  {prefix}: {exc}")


# ── Service management (launchd) ─────────────────────────────────

def _install_service():
    """Install the UI server as a macOS launchd service."""
    if not PLIST_SOURCE.exists():
        print(f"  ERROR: Plist not found at {PLIST_SOURCE}")
        sys.exit(1)

    # Unload first if already loaded (idempotent install)
    if PLIST_DEST.exists():
        subprocess.run(["launchctl", "unload", str(PLIST_DEST)],
                       capture_output=True)

    # Copy plist to LaunchAgents
    PLIST_DEST.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy2(str(PLIST_SOURCE), str(PLIST_DEST))

    # Load the service
    result = subprocess.run(["launchctl", "load", str(PLIST_DEST)],
                            capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: launchctl load failed: {result.stderr.strip()}")
        sys.exit(1)

    print(f"  Service installed and loaded: {LAUNCHD_LABEL}")
    print(f"  The server will start automatically at login.")
    print(f"  Use --status to check, --uninstall-service to remove.")


def _uninstall_service():
    """Remove the UI server launchd service."""
    if PLIST_DEST.exists():
        subprocess.run(["launchctl", "unload", str(PLIST_DEST)],
                       capture_output=True)
        PLIST_DEST.unlink()
        print(f"  Service unloaded and removed: {LAUNCHD_LABEL}")
    else:
        print(f"  Service not installed (no plist at {PLIST_DEST})")


def _check_status():
    """Check if the launchd service is loaded and running."""
    result = subprocess.run(
        ["launchctl", "list"],
        capture_output=True, text=True,
    )

    for line in result.stdout.split("\n"):
        if LAUNCHD_LABEL in line:
            parts = line.split("\t")
            pid = parts[0].strip() if len(parts) >= 1 else "-"
            status = parts[1].strip() if len(parts) >= 2 else "-"

            if pid == "-":
                print(f"  Service: {LAUNCHD_LABEL}")
                print(f"  Status:  LOADED but NOT RUNNING (exit code: {status})")
            else:
                print(f"  Service: {LAUNCHD_LABEL}")
                print(f"  Status:  RUNNING (PID {pid})")
            return

    # Not in launchctl list at all
    if PLIST_DEST.exists():
        print(f"  Service: {LAUNCHD_LABEL}")
        print(f"  Status:  INSTALLED but NOT LOADED")
        print(f"  Run: launchctl load {PLIST_DEST}")
    else:
        print(f"  Service: {LAUNCHD_LABEL}")
        print(f"  Status:  NOT INSTALLED")
        print(f"  Run: python scripts/start_ui.py --install-service")


# ── Main ─────────────────────────────────────────────────────────

def main():
    _ensure_venv()

    # Parse CLI flags
    parser = argparse.ArgumentParser(description="Market Digest UI Server")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--install-service", action="store_true",
                       help="Install as a macOS launchd service (auto-start at login)")
    group.add_argument("--uninstall-service", action="store_true",
                       help="Remove the macOS launchd service")
    group.add_argument("--status", action="store_true",
                       help="Check launchd service status")
    args = parser.parse_args()

    if args.install_service:
        _install_service()
        return
    if args.uninstall_service:
        _uninstall_service()
        return
    if args.status:
        _check_status()
        return

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

    # Open browser only on first start (not on restarts)
    import threading
    browser_opened = False

    import uvicorn

    restart_times = []
    consecutive_crashes = 0

    while True:
        _kill_stale_port()

        if not browser_opened:
            threading.Thread(
                target=lambda: (time.sleep(1.5), webbrowser.open(url)),
                daemon=True,
            ).start()
            browser_opened = True

        try:
            uvicorn.run("ui.server:app", host="0.0.0.0", port=PORT,
                        reload=False, log_level="warning")
        except KeyboardInterrupt:
            print("\n  Stopped by user.")
            break
        except SystemExit as e:
            # uvicorn raises SystemExit on SIGTERM — treat as clean shutdown
            if e.code == 0 or e.code is None:
                print("\n  Server stopped.")
                break
            # Non-zero SystemExit — treat as crash
            _log_crash(e)
            consecutive_crashes += 1
        except Exception as e:
            _log_crash(e)
            consecutive_crashes += 1
        else:
            # uvicorn returned normally (no exception) — still restart
            consecutive_crashes = 0

        # Track restart frequency
        now = time.time()
        restart_times.append(now)
        restart_times = [t for t in restart_times if now - t < RAPID_WINDOW]

        if len(restart_times) >= MAX_RAPID_RESTARTS:
            msg = (f"  Server crashed {MAX_RAPID_RESTARTS} times in "
                   f"{RAPID_WINDOW}s — giving up. Check logs/ui_server.log")
            print(f"\n{msg}")
            _log_crash(RuntimeError(msg), prefix="GAVE UP")
            sys.exit(1)

        backoff = min(2 ** consecutive_crashes, 30)
        print(f"\n  Restarting in {backoff}s... "
              f"(crash #{len(restart_times)} in last {RAPID_WINDOW}s)")
        time.sleep(backoff)


if __name__ == "__main__":
    main()
