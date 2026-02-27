#!/usr/bin/env python3
"""Generate & install launchd plists for macOS scheduling."""

import getpass
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PROJECT_ROOT = Path(__file__).parent.parent
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
_USERNAME = getpass.getuser()

# Hardcoded defaults if digests.yaml is missing or incomplete
DEFAULT_SCHEDULES = {
    "morning": "06:30",
    "afternoon": "16:30",
    "weekly": "fri 17:30",
    "daytrade": "08:15",
}

DIGEST_TYPES = ["morning", "afternoon", "weekly", "daytrade"]


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


def _parse_schedule(schedule_str: str) -> tuple[int, int, list[int]]:
    """Parse schedule string into (hour, minute, weekdays).

    Formats:
        "06:30"         -> (6, 30, [1,2,3,4,5])  (Mon-Fri)
        "fri 17:30"     -> (17, 30, [5])          (Friday only)
        "mon,wed 09:00" -> (9, 0, [1,3])          (Mon+Wed)
    """
    schedule_str = schedule_str.strip().lower()

    # Check for day prefix
    day_map = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7}
    weekdays = []

    parts = schedule_str.split()
    if len(parts) == 2:
        day_part, time_part = parts
        for day_str in day_part.split(","):
            day_str = day_str.strip()
            if day_str in day_map:
                weekdays.append(day_map[day_str])
    else:
        time_part = parts[0]

    # Default to Mon-Fri if no days specified
    if not weekdays:
        weekdays = [1, 2, 3, 4, 5]

    # Parse HH:MM
    match = re.match(r"(\d{1,2}):(\d{2})", time_part)
    if not match:
        raise ValueError(f"Invalid time format: {time_part}")

    hour = int(match.group(1))
    minute = int(match.group(2))
    return hour, minute, weekdays


def _generate_plist(label: str, digest_type: str, python_path: str,
                    hour: int, minute: int, weekdays: list[int]) -> str:
    """Generate a launchd plist XML string."""
    # Build calendar interval entries
    intervals = []
    for day in weekdays:
        intervals.append(
            f"        <dict>\n"
            f"            <key>Weekday</key><integer>{day}</integer>\n"
            f"            <key>Hour</key><integer>{hour}</integer>\n"
            f"            <key>Minute</key><integer>{minute}</integer>\n"
            f"        </dict>"
        )
    intervals_xml = "\n".join(intervals)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{PROJECT_ROOT}/scripts/run_digest.py</string>
        <string>--type</string>
        <string>{digest_type}</string>
    </array>

    <key>WorkingDirectory</key>
    <string>{PROJECT_ROOT}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string>
        <key>PYTHONPATH</key>
        <string>{PROJECT_ROOT}</string>
    </dict>

    <key>StartCalendarInterval</key>
    <array>
{intervals_xml}
    </array>

    <key>StandardOutPath</key>
    <string>{PROJECT_ROOT}/logs/{digest_type}_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>{PROJECT_ROOT}/logs/{digest_type}_stderr.log</string>
</dict>
</plist>
"""


def install():
    print("=" * 50)
    print("Market Digest — launchd Installer")
    print("=" * 50)

    python_path = find_python()
    print(f"\nDetected Python: {python_path}")

    # Load schedules from digests.yaml
    from config.settings import load_digest_config
    schedules = {}
    for dtype in DIGEST_TYPES:
        cfg = load_digest_config(dtype)
        schedule_str = cfg.get("schedule", DEFAULT_SCHEDULES.get(dtype, "06:30"))
        schedules[dtype] = str(schedule_str)

    LAUNCH_AGENTS.mkdir(exist_ok=True)

    schedule_summary = []

    for dtype in DIGEST_TYPES:
        label = f"com.{_USERNAME}.market-digest-{dtype}"
        plist_name = f"{label}.plist"
        dst = LAUNCH_AGENTS / plist_name

        schedule_str = schedules[dtype]
        try:
            hour, minute, weekdays = _parse_schedule(schedule_str)
        except ValueError as e:
            print(f"  WARNING: Bad schedule for {dtype} ({schedule_str}): {e}, using default")
            default_str = DEFAULT_SCHEDULES[dtype]
            hour, minute, weekdays = _parse_schedule(default_str)
            schedule_str = default_str

        # Generate plist dynamically
        plist_content = _generate_plist(label, dtype, python_path, hour, minute, weekdays)

        # Unload if already loaded
        subprocess.run(["launchctl", "unload", str(dst)], capture_output=True)

        # Write plist
        dst.write_text(plist_content)
        print(f"\n  Installed: {dst}")

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

        # Build summary
        day_names = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
        day_str = ",".join(day_names[d] for d in weekdays)
        schedule_summary.append(f"  {dtype.title():12s} {day_str} {hour:02d}:{minute:02d}")

    print("\n" + "=" * 50)
    print("Installation complete!")
    print("\nScheduled digests:")
    for line in schedule_summary:
        print(line)
    print("\nManagement commands:")
    print("  launchctl list | grep market-digest   # Check status")
    print(f"  launchctl start com.{_USERNAME}.market-digest-morning  # Run now")
    print(f"  launchctl unload ~/Library/LaunchAgents/com.{_USERNAME}.market-digest-morning.plist  # Disable")


def uninstall():
    print("Uninstalling market-digest launchd jobs...")
    for dtype in DIGEST_TYPES:
        plist_name = f"com.{_USERNAME}.market-digest-{dtype}.plist"
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
