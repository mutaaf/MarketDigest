# Linux Scheduling (systemd + cron)

## Running the Web UI as a Service

This keeps the web UI running in the background and auto-starts it after reboots.

### 1. Copy the service file

```bash
# Replace YOUR_USER with your Linux username
sudo cp systemd/market-digest.service /etc/systemd/system/market-digest@.service
```

### 2. Edit paths if needed

If your project isn't at `~/market-digest`, edit the service file:

```bash
sudo nano /etc/systemd/system/market-digest@.service
# Update WorkingDirectory and ExecStart paths
```

### 3. Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable market-digest@YOUR_USER
sudo systemctl start market-digest@YOUR_USER
```

### 4. Check status

```bash
sudo systemctl status market-digest@YOUR_USER
```

## Scheduling Digests with Cron

Use cron to run digests on a schedule (similar to macOS launchd).

```bash
crontab -e
```

Add lines like these (adjust paths to match your setup):

```cron
# Morning digest at 6:30 AM (Mon-Fri)
30 6 * * 1-5 cd /home/YOUR_USER/market-digest && .venv/bin/python scripts/run_digest.py --type morning --mode full

# Day trade picks at 8:15 AM (Mon-Fri)
15 8 * * 1-5 cd /home/YOUR_USER/market-digest && .venv/bin/python scripts/run_digest.py --type daytrade --mode full

# Afternoon recap at 4:30 PM (Mon-Fri)
30 16 * * 1-5 cd /home/YOUR_USER/market-digest && .venv/bin/python scripts/run_digest.py --type afternoon --mode full

# Weekly summary at 5:30 PM Friday
30 17 * * 5 cd /home/YOUR_USER/market-digest && .venv/bin/python scripts/run_digest.py --type weekly --mode full
```

## Uninstalling

```bash
sudo systemctl stop market-digest@YOUR_USER
sudo systemctl disable market-digest@YOUR_USER
sudo rm /etc/systemd/system/market-digest@.service
sudo systemctl daemon-reload
```
