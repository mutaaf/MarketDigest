# macOS Scheduling (launchd)

The `.plist` files in this directory are auto-generated — do not edit them manually.

## Setup

```bash
.venv/bin/python scripts/setup_launchd.py
```

This reads your schedules from `config/digests.yaml` and installs launchd jobs that run each digest type at the configured time (Mon–Fri by default).

## Management

```bash
# Check which jobs are loaded
launchctl list | grep market-digest

# Manually trigger a digest
launchctl start com.<username>.market-digest-morning

# Disable a digest
launchctl unload ~/Library/LaunchAgents/com.<username>.market-digest-morning.plist

# Uninstall all jobs
.venv/bin/python scripts/setup_launchd.py --uninstall
```

## Default Schedule

| Digest    | Time (CT) | Days    |
|-----------|-----------|---------|
| Morning   | 06:30     | Mon–Fri |
| Daytrade  | 08:15     | Mon–Fri |
| Afternoon | 16:30     | Mon–Fri |
| Weekly    | 17:30     | Friday  |

Edit schedules in `config/digests.yaml` or via the web UI, then re-run the setup script.
