# Screenshots for README

This directory holds screenshots used in the project README. You need to capture these from your running instance with real market data.

## What to Capture

### 1. `dashboard.png` — Command Center Home Page
- Open `http://localhost:8550` in your browser
- Make sure API health dots are visible (green = connected)
- Show the main navigation and digest controls
- **Crop to:** Full browser window, 1200px wide

### 2. `scorecard.png` — ScoreCard Detail Panel
- Navigate to the ScoreCard page
- Click into a high-scoring instrument (look for an A or B grade)
- Show the grade badge, entry/target/stop levels, RSI zones
- For a stock, make sure the fundamentals panel is visible
- **Crop to:** The detail panel, 1200px wide

### 3. `telegram.png` — Telegram Digest Message
- Open Telegram on your phone
- Find a real digest message from the bot
- Screenshot the full message showing formatted output with scored picks
- **Crop to:** Phone screen, centered on the message

### 4. `retrace.png` — Retrace Performance Page
- Navigate to the Retrace page in the web UI
- Show win rate stats and pick performance history
- Best if you have a few days of data so the tracking is visible
- **Crop to:** Full page, 1200px wide

## Recording a Demo GIF

A GIF of the workflow is the single highest-impact visual you can add.

**What to show (15 seconds max):**
1. Open browser → Command Center dashboard
2. Click into ScoreCard → show a graded instrument
3. Quick scroll through picks
4. Switch to Telegram → show digest on phone (or use phone screenshot overlay)

**Tools:**
- **macOS:** Built-in screen recording (Cmd+Shift+5) → convert with `ffmpeg -i recording.mov -vf "fps=10,scale=800:-1" demo.gif`
- **Cross-platform:** [LICEcap](https://www.cockos.com/licecap/) (free, records directly to GIF)
- **Optimize:** `gifsicle -O3 --lossy=80 demo.gif -o demo.gif` to get under 5MB

Save the GIF as `demo.gif` in this directory.

## Specs

- **Width:** 1200px max for screenshots, 800px for GIF
- **Format:** PNG for screenshots, GIF for demo
- **Size:** Under 500KB per screenshot, under 5MB for GIF
- **Naming:** Exact filenames listed above (dashboard.png, scorecard.png, telegram.png, retrace.png, demo.gif)

Once captured, uncomment the image tags in the root `README.md` to display them.
