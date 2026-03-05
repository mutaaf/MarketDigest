<div align="center">

# Market Digest

**Your entire pre-market routine — automated, scored, and delivered to your phone.**

[![GitHub Stars](https://img.shields.io/github/stars/mutaaf/market-digest?style=flat&color=yellow)](https://github.com/mutaaf/market-digest/stargazers)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776ab.svg)](https://python.org)
[![CI](https://github.com/mutaaf/MarketDigest/actions/workflows/ci.yml/badge.svg)](https://github.com/mutaaf/MarketDigest/actions)

**Tired of checking 6 different websites before the market opens?**<br>
Market Digest does it for you. It grabs live prices, analyzes every instrument, gives each one a score from 0 to 100, and sends you a clean summary on Telegram.<br>
Then it tracks whether those picks actually worked — so your results improve over time.

<!-- TODO: Add demo GIF here. See assets/screenshots/README.md for recording instructions. -->
![Market Digest Demo](assets/screenshots/demo.gif)

</div>

---

## What You Get

<table>
<tr>
<td width="60">📱</td>
<td><strong>A market summary on your phone every morning</strong><br>Before you even open your laptop, a scored brief — morning, afternoon, weekly, or day trade — is already waiting in Telegram.</td>
</tr>
<tr>
<td>🎯</td>
<td><strong>Clear entry, target, and stop levels</strong><br>Every instrument gets a grade from A+ to F, plus exact price levels: where to buy, where to take profit, and where to cut your loss.</td>
</tr>
<tr>
<td>📊</td>
<td><strong>See which picks actually worked</strong><br>The <strong>Retrace</strong> system saves every pick you get, then checks the next day — did it hit the target? Did it hit the stop? You'll see your actual win rate.</td>
</tr>
<tr>
<td>🧠</td>
<td><strong>Optional AI analysis</strong><br>Connect Claude, ChatGPT, or Gemini and get AI-written commentary alongside your data. Or skip it entirely — the core system needs zero AI to work.</td>
</tr>
<tr>
<td>🖥️</td>
<td><strong>A full control panel in your browser</strong><br>The <strong>Command Center</strong> lets you tweak settings, preview digests, see scorecards, and track performance — all from a clean web interface.</td>
</tr>
<tr>
<td>🔒</td>
<td><strong>Runs on your computer. Nobody else's.</strong><br>No cloud service. No monthly fee. No company storing your data. Everything stays on your machine.</td>
</tr>
</table>

> **New to trading terms?** Don't worry — this README explains everything in plain English.
> If you see something you don't understand, [open a discussion](https://github.com/mutaaf/market-digest/discussions) and we'll help.

---

## See It In Action

<details>
<summary>📸 <strong>Command Center Dashboard</strong> — click to expand</summary>
<br>

<!-- TODO: Screenshot of the Command Center home page showing API health indicators -->
![Dashboard](assets/screenshots/dashboard.png)

*The home page shows you which data sources are connected (green = good), quick buttons to run digests, and a snapshot of your setup.*

</details>

<details>
<summary>📊 <strong>Multi-Timeframe ScoreCard</strong> — click to expand</summary>
<br>

<!-- TODO: Screenshot of a ScoreCard detail panel -->
![ScoreCard](assets/screenshots/scorecard.png)

*Every instrument gets three grades: one for day trading (daily analysis), one for swing trading (weekly), and one for long-term (monthly). Click any instrument to see exactly why it scored the way it did — RSI, trend direction, how close it is to key price levels, and more.*

</details>

<details>
<summary>📱 <strong>What the Telegram Message Looks Like</strong> — click to expand</summary>
<br>

<!-- TODO: Screenshot of a Telegram message on your phone -->
![Telegram](assets/screenshots/telegram.png)

*A clean, formatted message on your phone with your top picks, scores, entry/target/stop levels, and market context. Ready to read in under a minute.*

</details>

<details>
<summary>🔄 <strong>Retrace — Performance Tracking</strong> — click to expand</summary>
<br>

<!-- TODO: Screenshot of the Retrace tracking page -->
![Retrace](assets/screenshots/retrace.png)

*After a few days of running, you'll see your actual hit rate: how often picks reached their target, how often they hit the stop, and how the scoring is performing. Use this to fine-tune your settings.*

</details>

---

## What You Need Before Starting

Just two things:

1. **A computer** — Mac, Windows, or Linux all work
2. **Python** — this is a free programming tool that runs Market Digest behind the scenes. You don't need to learn it — you just need it installed.

**How to check if you already have Python:**
- On **Mac**: open the **Terminal** app (press `Cmd + Space`, type `Terminal`, hit Enter), then type `python3 --version` and press Enter. If you see a number like `Python 3.12.0`, you're good.
- On **Windows**: open **PowerShell** (click the Start menu, type `PowerShell`, hit Enter), then type `python --version` and press Enter. If you see a number, you're good.

**Don't have Python?** Download it free from [python.org/downloads](https://www.python.org/downloads/) — click the big yellow button, run the installer, and accept the defaults. **Windows users:** make sure to check the box that says "Add Python to PATH" during installation.

That's all you need. No other software required.

---

## How to Install

### Step 1: Download Market Digest

**Easiest way — download as a ZIP file (no extra software needed):**

1. Click this link: [**Download Market Digest ZIP**](https://github.com/mutaaf/market-digest/archive/refs/heads/main.zip)
2. Your browser will download a `.zip` file
3. Find the downloaded file and **unzip it** (double-click it on Mac, or right-click → "Extract All" on Windows)
4. You'll get a folder called `market-digest-main` — move it somewhere easy to find, like your Desktop

### Step 2: Run the Setup

Now you need to open a **Terminal** (Mac/Linux) or **PowerShell** (Windows). This is just a text-based way to talk to your computer — you'll copy and paste a few commands.

**How to open it:**
- **Mac**: Press `Cmd + Space` to open Spotlight, type `Terminal`, press Enter
- **Windows**: Click the Start menu, type `PowerShell`, press Enter
- **Linux**: Press `Ctrl + Alt + T`

Once it's open, type these commands one at a time, pressing **Enter** after each one:

**First, navigate to the folder you just unzipped:**

On Mac/Linux (if you put it on your Desktop):
```bash
cd ~/Desktop/market-digest-main
```

On Windows (if you put it on your Desktop):
```powershell
cd ~\Desktop\market-digest-main
```

> **What this does:** tells your computer to look inside the Market Digest folder.

**Next, run the setup:**

On Mac/Linux:
```bash
chmod +x setup.sh
./setup.sh
```

On Windows:
```powershell
.\setup.bat
```

> **What this does:** installs everything Market Digest needs. It will ask you about some optional account passwords (called "API keys") — **you can skip all of them for now** by pressing Enter. You can always add them later.
>
> **What you should see:** text scrolling by as it installs. This takes 1-2 minutes. When it's done, you'll see a success message.

### Step 3: Start Market Digest

On Mac:
```bash
./start.command
```
> You can also just **double-click** the `start.command` file in the folder — it does the same thing.

On Windows:
```powershell
.venv\Scripts\python scripts\start_ui.py
```

On Linux:
```bash
.venv/bin/python scripts/start_ui.py
```

> **What happens:** a page will open in your browser automatically — that's the **Command Center**, your control panel for everything. If it doesn't open automatically, go to [localhost:8550](http://localhost:8550) in your browser.

**That's it — you're running!** 🎉

---

### See a Sample Digest Right Now

No accounts or extra setup needed. In the same Terminal/PowerShell window, run:

On Mac/Linux:
```bash
.venv/bin/python scripts/run_digest.py --type daytrade --mode facts --dry-run
```

On Windows:
```powershell
.venv\Scripts\python scripts\run_digest.py --type daytrade --mode facts --dry-run
```

> **What this does:** pulls free stock data and shows you a scored day trade digest right in your Terminal. It's a preview — to get digests on your phone, set up Telegram below (free, takes 2 minutes).

---

### Stuck? Common Issues

| Problem | Fix |
|---------|-----|
| **"permission denied"** when running `setup.sh` | Run `chmod +x setup.sh` first, then try again |
| **"python3 not found"** or **"python not found"** | Python isn't installed yet — [download it here](https://www.python.org/downloads/) |
| **Windows: "running scripts is disabled"** | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` in PowerShell, then try again |
| **The browser page didn't open** | Open your browser and go to [localhost:8550](http://localhost:8550) |
| **Something else went wrong** | [Open an issue](https://github.com/mutaaf/market-digest/issues/new/choose) — tell us what happened and what system you're on, and we'll help |

<details>
<summary>🛠️ <strong>For techies: Git clone, Docker, and manual setup</strong></summary>
<br>

**Git clone (instead of ZIP download):**
```bash
git clone https://github.com/mutaaf/market-digest.git
cd market-digest
./setup.sh
```

**Docker:**
```bash
git clone https://github.com/mutaaf/market-digest.git
cd market-digest
cp .env.example .env    # Optional: edit .env with your API keys
docker compose up --build
```
Open [localhost:8550](http://localhost:8550) in your browser. Done.

**Full manual setup:**
```bash
git clone https://github.com/mutaaf/market-digest.git
cd market-digest

# Create an isolated Python environment
python3 -m venv .venv
source .venv/bin/activate          # On Windows: .venv\Scripts\activate

# Install Python packages
pip install -r requirements.txt

# Create your config file
cp .env.example .env

# Build the web interface (needs Node.js — https://nodejs.org)
cd ui/frontend && npm install && npm run build && cd ../..

# Start everything
python scripts/start_ui.py
```

**Makefile shortcuts** (requires `make`, which is pre-installed on Mac/Linux):
```bash
make setup          # Full setup (venv + deps + frontend build)
make ui             # Start the web UI
make dev            # Start with hot-reload (development)
make digest-dry     # Quick dry-run daytrade digest
make test           # Run tests
make lint           # Run linter
make clean          # Remove build artifacts and cache
make help           # Show all available targets
```

</details>

---

## How It Works — The Simple Version

Think of Market Digest as a robot assistant that does your pre-market homework:

```
   You sleep               Market Digest works            You wake up
  ┌──────────┐          ┌──────────────────────┐        ┌────────────┐
  │  😴 zzz  │          │  1. Grab live prices  │        │  📱 Phone  │
  │          │          │  2. Run analysis      │  ───▶  │   buzzes   │
  │          │          │  3. Score everything  │        │  "Here are │
  │          │          │  4. Pick the best     │        │  today's   │
  │          │          │  5. Send to Telegram  │        │  top picks"│
  └──────────┘          └──────────────────────┘        └────────────┘
```

**Here's what happens under the hood:**

1. **Grabs data from 6 free sources** — live prices (yfinance), intraday data (TwelveData), earnings info (Finnhub), economic indicators like interest rates and GDP (FRED), financial news (NewsAPI), and market fear/greed levels.

2. **Analyzes everything across 3 timeframes:**
   - **Daily** — for day trades (buying and selling the same day)
   - **Weekly** — for swing trades (holding for days to weeks)
   - **Monthly** — for long-term positions (holding for weeks to months)

3. **Scores each instrument from 0 to 100** using:
   - **RSI** (Relative Strength Index) — measures if something is overbought (too expensive, might drop) or oversold (cheap, might bounce)
   - **Trend direction** — is the price going up, down, or sideways?
   - **Pivot proximity** — how close is the price to key support/resistance levels (floors and ceilings)?
   - **Volatility** — how wild are the price swings?
   - **Volume** — are more people trading it than usual?
   - **Gap analysis** — did the price jump overnight?

4. **For stocks, it also checks the business fundamentals:**
   - Is the company fairly valued? (valuation)
   - Is it making good money? (profitability)
   - Is it growing? (growth)
   - Is it financially healthy? (debt, cash flow)

5. **Sends you a formatted summary** on Telegram with the top picks, their scores, and exact entry/target/stop price levels.

6. **Tracks accuracy** — the Retrace system records every pick and checks the next day: did the price hit the target? Over time, you'll see which types of picks work best and can adjust the scoring weights.

---

## What You Can Track

84 instruments come pre-loaded across 7 categories. You can add, remove, or toggle any of them:

| Category | What's Included | Count |
|----------|----------------|-------|
| **US Stocks** | Apple, NVIDIA, Tesla, Meta, Amazon, JPMorgan, Eli Lilly, Palantir, and 40 more | 48 |
| **US Indices** | S&P 500, NASDAQ, Dow Jones, VIX (the "fear index") | 6 |
| **Forex** | EUR/USD, GBP/USD, USD/JPY (currency pairs) | 8 |
| **Commodities** | Gold, Silver, Oil, Natural Gas, Coffee, Copper, Wheat, and more | 14 |
| **Crypto** | Bitcoin, Ethereum, Solana, XRP, Cardano | 5 |
| **Futures** | S&P 500 Futures, NASDAQ Futures, Dow Futures | 3 |
| **Economic Data** | Fed interest rate, CPI (inflation), GDP, unemployment | 8 |

> **Want to add something?** Open the Command Center → Instruments page, and add any ticker. Or edit `config/instruments.yaml` directly.

---

## API Keys — What's Free, What's Optional

**Market Digest works right away with zero API keys and zero signups.** The core data source (yfinance) is completely free and built in.

Everything else is optional — add keys later to unlock more data. (API keys are like free account passwords that let Market Digest connect to extra data services.)

| Service | Do I Need It? | Cost | What It Adds | Sign Up |
|---------|:---:|------|--------------|---------|
| **yfinance** | Already included | Free | Stock prices, fundamentals — this is the engine | No signup needed |
| **Telegram** | Only if you want phone delivery | Free | Get digests sent to your phone | [See setup guide below](#setting-up-telegram--get-digests-on-your-phone) |
| **TwelveData** | No | Free (800 calls/day) | Better real-time and intraday prices | [Sign up](https://twelvedata.com) |
| **Finnhub** | No | Free (60 calls/min) | Earnings dates, economic events | [Sign up](https://finnhub.io) |
| **FRED** | No | Free (unlimited) | Fed rate, GDP, inflation, unemployment | [Get key](https://fred.stlouisfed.org/docs/api/api_key.html) |
| **NewsAPI** | No | Free (100 calls/day) | Financial news headlines | [Sign up](https://newsapi.org) |
| **Claude / ChatGPT / Gemini** | No | Varies (has free tiers) | AI-written commentary on digests | [Anthropic](https://console.anthropic.com) / [OpenAI](https://platform.openai.com) / [Google](https://aistudio.google.com) |

> **How to add keys:** Open the Command Center (Settings page) to enter them through the web interface. Or edit the `.env` file in the project folder. Or re-run `./setup.sh` and enter them when prompted.
>
> **Our recommendation:** Start with zero keys. Run a sample digest to see how it works. Then add Telegram when you're ready for phone delivery. Add the rest whenever you feel like it.

---

## Setting Up Telegram — Get Digests on Your Phone

Telegram is free and takes about 2 minutes to set up. Once connected, Market Digest will send formatted digests directly to your phone — no app to open, no website to check.

### Step 1: Create a Telegram Bot

1. **Open Telegram** on your phone or computer (download it from [telegram.org](https://telegram.org) if you don't have it — it's free)
2. **Search for `@BotFather`** in Telegram and open a chat with it (BotFather is Telegram's official tool for creating bots)
3. **Send the message:** `/newbot`
4. **BotFather will ask you two things:**
   - A **name** for your bot (this is a display name, e.g., `My Market Digest`)
   - A **username** for your bot (must end in `bot`, e.g., `my_market_digest_bot`)
5. **BotFather will reply with a token** — a long string that looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`. **Copy this token.** You'll need it in Step 3.

### Step 2: Get Your Chat ID

Your Chat ID tells Market Digest *where* to send messages (your personal chat).

1. **Open a chat with your new bot** in Telegram — search for the username you just created
2. **Send it any message** (just say "hello" — the bot won't reply yet, that's normal)
3. **Open this URL in your browser** (replace `YOUR_TOKEN` with the token from Step 1):
   ```
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```
4. **Look for `"chat":{"id":` in the response** — the number after it is your Chat ID (e.g., `987654321`)

> **Can't find your Chat ID?** An easier method: search for `@userinfobot` on Telegram, start a chat, and it'll tell you your ID.

### Step 3: Add Your Credentials

Open the **Command Center** (Settings page) and enter your Bot Token and Chat ID there. Or, if you prefer, edit the `.env` file in the project folder:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
```

### Step 4: Test It

In your Terminal/PowerShell, run:

On Mac/Linux:
```bash
.venv/bin/python scripts/test_telegram.py
```

On Windows:
```powershell
.venv\Scripts\python scripts\test_telegram.py
```

> If it works, you'll get a test message on Telegram. If not, double-check that you messaged the bot first (Step 2) and that the token and chat ID are correct.

**That's it — you're connected.** Now any digest you run will be delivered to your phone.

> **Want to send to multiple people?** Add more chat IDs separated by commas:
> ```env
> TELEGRAM_CHAT_ID=987654321,111222333,444555666
> ```
> Each person needs to have opened a chat with your bot first.

---

## Bring Your Own Data Sources

Market Digest comes with 6 built-in data sources, but you can **add your own** — any HTTP API, RSS feed, or CSV file — through the Command Center or the API. No code required.

### Adding a Custom Source via the Command Center

1. Open the Command Center (double-click `start.command` on Mac, or run `start_ui.py` — see [How to Install](#how-to-install))
2. Go to the **Data Sources** page
3. Click **Add Custom Source**
4. Fill in the details:
   - **Name** — whatever you want to call it (e.g., "Alpha Vantage", "My RSS Feed")
   - **Type** — `HTTP API`, `RSS Feed`, or `CSV File`
   - **URL** — the endpoint or feed URL
   - **Authentication** — API key, Bearer token, or custom header (if needed)
5. Click **Test** to verify it connects
6. Enable it — the data will now appear in your digests

### Three Source Types

<details>
<summary><strong>HTTP API</strong> — connect to any JSON API</summary>
<br>

Point it at any REST API that returns JSON. Market Digest handles:
- **URL templates** — use `{symbol}` and `{api_key}` placeholders (e.g., `https://api.example.com/quote/{symbol}?key={api_key}`)
- **Authentication** — API key in URL, Bearer token, or custom header
- **Response mapping** — tell it which fields in the API response map to `price`, `open`, `high`, `low`, etc.
- **Per-symbol fetching** — specify a list of symbols and it'll call the API for each one

</details>

<details>
<summary><strong>RSS Feed</strong> — pull in any news feed</summary>
<br>

Point it at any RSS or Atom feed URL (e.g., a financial news RSS feed, a subreddit feed, a blog). Market Digest will:
- Parse the feed automatically
- Pull title, summary, and link from each item
- Include the latest items in your digest

</details>

<details>
<summary><strong>CSV File</strong> — use your own local data</summary>
<br>

Point it at a CSV file on your computer. Useful for:
- Proprietary data you export from another tool
- Watchlists from your broker
- Custom research data

Market Digest reads the CSV, maps columns to fields, and auto-converts numbers.

</details>

<details>
<summary><strong>Example: Adding an HTTP API Source via the API</strong></summary>
<br>

Here's what it looks like to add Alpha Vantage as a custom source programmatically:

```bash
curl -X POST http://localhost:8550/api/sources/custom \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alpha Vantage",
    "type": "http",
    "url": "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}",
    "auth": {
      "env_var": "ALPHA_VANTAGE_KEY"
    },
    "instruments": ["AAPL", "MSFT"],
    "response_root": "Global Quote",
    "response_mapping": {
      "price": "05. price",
      "open": "02. open",
      "high": "03. high",
      "low": "04. low",
      "volume": "06. volume"
    }
  }'
```

</details>

> **Bottom line:** If it's on the internet and returns data, you can probably plug it in. No need to write code or modify source files — the Command Center handles everything.

---

## The Command Center — Your Control Panel

Start it by double-clicking `start.command` (Mac) or running the start command from [How to Install](#how-to-install). A page will open in your browser — that's the Command Center.

| Page | What You'll Do There |
|------|---------------------|
| **Dashboard** | See which data sources are connected, quick-launch digests |
| **Digest** | Preview any digest (morning, afternoon, weekly, day trade) and send it |
| **Instruments** | Turn instruments on/off, add new tickers, organize by category |
| **Data Sources** | Manage built-in sources, add custom APIs/RSS/CSV feeds, test connections |
| **ScoreCard** | See every instrument's grade (A+ to F) across all three timeframes |
| **Weights** | Adjust how much each factor matters in the scoring (e.g., "care more about trends, less about volume") |
| **Prompts** | Customize the AI prompts if you're using Claude/GPT/Gemini |
| **Retrace** | See your pick accuracy — which calls hit, which missed |
| **Settings** | Change your timezone, delivery preferences, enter API keys, and more |
| **Cache** | See what data is cached and clear it if needed |
| **Logs** | Browse past digests and system logs |

> **Access from your phone or tablet:** If your computer and phone are on the same Wi-Fi, you can open the Command Center on your phone's browser too. On your computer, find your IP address (Mac: open Terminal and run `ipconfig getifaddr en0` / Windows: open PowerShell and run `ipconfig`), then on your phone go to `http://YOUR_IP:8550`.

---

## Automate It — Set It and Forget It

The real power is automation. Set up a schedule and digests arrive on your phone without you lifting a finger.

<details>
<summary><strong>Mac</strong></summary>
<br>

In Terminal, navigate to your Market Digest folder and run:
```bash
.venv/bin/python scripts/setup_launchd.py
```

This sets up automatic runs:
| Digest | When |
|--------|------|
| Morning brief | 6:30 AM CT |
| Day trade picks | 8:15 AM CT |
| Afternoon recap | 4:30 PM CT |
| Weekly summary | Friday 5:30 PM CT |

Your computer needs to be awake at those times for the digests to run.

</details>

<details>
<summary><strong>Linux</strong></summary>
<br>

See [`systemd/README.md`](systemd/README.md) for service files and timer setup.

</details>

<details>
<summary><strong>Windows / Any system</strong></summary>
<br>

You can run any digest from PowerShell or Terminal:

```bash
.venv/bin/python scripts/run_digest.py --type daytrade --mode facts
```

**Digest types:** `morning`, `afternoon`, `weekly`, `daytrade`
**Modes:** `facts` (data only), `full` (data + AI commentary), `both` (sends both separately)

Use Windows Task Scheduler (or cron on Mac/Linux) to run these commands automatically at whatever times you choose.

</details>

---

## Frequently Asked Questions

<details>
<summary><strong>Do I need to know how to code?</strong></summary>
<br>

Nope. If you can copy-paste a few commands, you can run Market Digest. The setup script handles everything. The Command Center (web interface) handles all configuration — no code editing required.

</details>

<details>
<summary><strong>Is this free?</strong></summary>
<br>

Yes, completely. Market Digest is open source under the MIT license. No premium tier, no trial period, no catch. The data sources it uses have generous free tiers. You can run it forever without paying anything.

</details>

<details>
<summary><strong>Is this financial advice?</strong></summary>
<br>

No. Market Digest is a data analysis tool. It scores instruments based on technical and fundamental indicators, but it doesn't tell you what to buy or sell. Always do your own research and never trade money you can't afford to lose.

</details>

<details>
<summary><strong>What's "self-hosted" mean?</strong></summary>
<br>

It means the software runs on your own computer, not on someone else's server. Your data stays with you. There's no company collecting your information or charging you monthly. The downside: you have to run the setup yourself (but it's a one-time thing).

</details>

<details>
<summary><strong>Can I run this on a Raspberry Pi / VPS / server?</strong></summary>
<br>

Yes — anywhere that runs Python 3.10+ and has internet access. A Raspberry Pi 4, a $5/month VPS, an old laptop — all work great. Docker makes it especially easy on servers.

</details>

<details>
<summary><strong>What if something breaks?</strong></summary>
<br>

[Open an issue](https://github.com/mutaaf/market-digest/issues/new/choose) with what happened and we'll help. Include your operating system and Python version.

</details>

<details>
<summary><strong>Can I add my own stocks/instruments?</strong></summary>
<br>

Yes, two ways: through the Command Center (Instruments page → Add), or by editing `config/instruments.yaml`. Any ticker that works on [Yahoo Finance](https://finance.yahoo.com) works here.

</details>

<details>
<summary><strong>My Telegram bot isn't sending messages</strong></summary>
<br>

The most common fixes:

1. **Did you message the bot first?** Open Telegram, find your bot by its username, and send it any message (even just "hi"). The bot can't message you until you've started a conversation with it.
2. **Is your token correct?** Copy it again from BotFather — make sure there are no extra spaces.
3. **Is your Chat ID correct?** Try the `@userinfobot` method: search for `@userinfobot` on Telegram, send it a message, and it'll reply with your ID.
4. **Run the test:** In Terminal/PowerShell, run `.venv/bin/python scripts/test_telegram.py` (on Windows: `.venv\Scripts\python scripts\test_telegram.py`) — it'll tell you exactly what's wrong.

</details>

<details>
<summary><strong>Can I use Discord / Email / Slack instead of Telegram?</strong></summary>
<br>

Not yet built in, but Telegram is free and takes 2 minutes to set up. Discord and email delivery are on the roadmap. If you're a developer, the delivery system in `src/delivery/` is modular — adding a new delivery method is a great first contribution.

</details>

<details>
<summary><strong>Can I plug in my own data source?</strong></summary>
<br>

Yes — any HTTP API, RSS feed, or CSV file. No code needed. Use the Command Center's Data Sources page or the REST API. See the [Bring Your Own Data Sources](#bring-your-own-data-sources) section for details and examples.

</details>

---

## For Developers

<details>
<summary><strong>Configuration</strong></summary>
<br>

All config is in YAML files under `config/`. Edit by hand or through the web UI — changes apply instantly, no restart needed.

| File | Controls |
|------|----------|
| `config/instruments.yaml` | Which instruments to track (tickers, names, categories) |
| `config/scoring.yaml` | Scoring weights for day trade, swing, and long-term timeframes |
| `config/prompts.yaml` | LLM prompt templates and AI provider settings |
| `config/digests.yaml` | Digest sections, modes, and delivery schedules |

</details>

<details>
<summary><strong>Architecture</strong></summary>
<br>

```
┌─────────────────────────────────────────────────────────────┐
│                    Web UI (React + Vite)                     │
│              localhost:8550 — Command Center                 │
├─────────────────────────────────────────────────────────────┤
│                  FastAPI Server (60 endpoints)               │
├──────────┬──────────┬───────────┬───────────┬───────────────┤
│ Fetchers │ Analysis │  Digest   │  Retrace  │    Config     │
│ yfinance │ RSI/MACD │ Morning   │ Snapshot  │ instruments   │
│ 12Data   │ Pivots   │ Afternoon │ Grading   │ prompts       │
│ Finnhub  │ Trend    │ Weekly    │ Scoring   │ digests       │
│ FRED     │ Scoring  │ Daytrade  │ Tracking  │ scoring wts   │
│ NewsAPI  │ LLM      │ Formatter │           │               │
│ F&G      │ Fundmtls │           │           │               │
├──────────┴──────────┴───────────┴───────────┴───────────────┤
│          Cache (memory + JSON)  │  Telegram Delivery         │
└─────────────────────────────────┴───────────────────────────┘
```

**Tech stack:** Python 3.12 + FastAPI (60 endpoints), React 18 + TypeScript + Vite + Tailwind (web UI), yfinance + TwelveData + Finnhub + FRED + NewsAPI (data), dual-tier cache (memory + JSON files), Telegram for delivery. No database — all persistence is YAML configs and JSON files.

</details>

<details>
<summary><strong>Project Structure</strong></summary>
<br>

```
market-digest/
├── config/              # YAML configs (instruments, prompts, scoring weights)
├── src/
│   ├── analysis/        # Technical analysis, scoring, LLM, fundamentals
│   ├── cache/           # Dual-tier cache (memory + JSON files)
│   ├── delivery/        # Telegram delivery
│   ├── digest/          # Digest builders (morning, afternoon, weekly, daytrade)
│   ├── fetchers/        # Data fetchers (yfinance, TwelveData, Finnhub, etc.)
│   ├── retrace/         # Pick snapshot & grading system
│   └── utils/           # Logging, rate limiting, timezone helpers
├── ui/
│   ├── server.py        # FastAPI app (11 route groups)
│   ├── routes/          # API route handlers
│   └── frontend/        # React + TypeScript + Tailwind
├── scripts/             # CLI tools (run_digest, start_ui, setup_launchd, etc.)
├── tests/               # Test suite
├── logs/                # Runtime logs & retrace snapshots
└── cache/               # File-backed JSON cache
```

</details>

---

## Contributing

Want to help make Market Digest better? See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and how to add new features.

---

## License

[MIT](LICENSE) — use it however you want, for free, forever.
