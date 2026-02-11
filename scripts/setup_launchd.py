#!/usr/bin/env python3
"""Generate & install launchd plists for macOS scheduling."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PROJECT_ROOT = Path(__file__).parent.parent
LAUNCHD_SRC = PROJECT_ROOT / "launchd"
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"

PLIST_FILES = [
    "com.mutaafaziz.market-digest-morning.plist",
    "com.mutaafaziz.market-digest-afternoon.plist",
    "com.mutaafaziz.market-digest-weekly.plist",
]


def find_python() -> str:
    """Find the best Python 3 path on this system."""
    candidates = [
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        shutil.which("python3"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return sys.executable


def update_plist_python_path(plist_path: Path, python_path: str) -> None:
    """Update the Python path in a plist file to match the local system."""
    content = plist_path.read_text()
    # Replace the default python path with the detected one
    content = content.replace("/usr/local/bin/python3", python_path)
    plist_path.write_text(content)


def install():
    print("=" * 50)
    print("Market Digest — launchd Installer")
    print("=" * 50)

    python_path = find_python()
    print(f"\nDetected Python: {python_path}")

    LAUNCH_AGENTS.mkdir(exist_ok=True)

    for plist_name in PLIST_FILES:
        src = LAUNCHD_SRC / plist_name
        dst = LAUNCH_AGENTS / plist_name

        if not src.exists():
            print(f"  WARNING: {src} not found, skipping")
            continue

        # Copy plist
        shutil.copy2(src, dst)
        update_plist_python_path(dst, python_path)
        print(f"\n  Installed: {dst}")

        # Unload if already loaded
        subprocess.run(
            ["launchctl", "unload", str(dst)],
            capture_output=True,
        )

        # Load the plist
        result = subprocess.run(
            ["launchctl", "load", str(dst)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"  Loaded: {plist_name}")
        else:
            print(f"  WARNING: Failed to load {plist_name}: {result.stderr}")

    print("\n" + "=" * 50)
    print("Installation complete!")
    print("\nScheduled digests:")
    print("  Morning:   Mon-Fri 6:30 AM CT")
    print("  Afternoon: Mon-Fri 4:30 PM CT")
    print("  Weekly:    Friday  5:30 PM CT")
    print("\nManagement commands:")
    print("  launchctl list | grep market-digest   # Check status")
    print("  launchctl start com.mutaafaziz.market-digest-morning  # Run now")
    print("  launchctl unload ~/Library/LaunchAgents/com.mutaafaziz.market-digest-morning.plist  # Disable")


def uninstall():
    print("Uninstalling market-digest launchd jobs...")
    for plist_name in PLIST_FILES:
        dst = LAUNCH_AGENTS / plist_name
        if dst.exists():
            subprocess.run(["launchctl", "unload", str(dst)], capture_output=True)
            dst.unlink()
            print(f"  Removed: {plist_name}")
        else:
            print(f"  Not found: {plist_name}")
    print("Done.")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        uninstall()
    else:
        install()


if __name__ == "__main__":
    main()
