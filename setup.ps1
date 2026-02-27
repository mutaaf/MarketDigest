# ──────────────────────────────────────────────────────────────
# Market Digest — Interactive Setup (Windows)
# ──────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "  Market Digest — Setup" -ForegroundColor Cyan
Write-Host "  ────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

function Write-Ok($msg)   { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  ! $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "  ✗ $msg" -ForegroundColor Red }
function Write-Info($msg) { Write-Host "  → $msg" -ForegroundColor Blue }

# ── Step 1: Check Python ─────────────────────────────────────
Write-Host "Step 1/5: Checking Python..."

$python = $null
foreach ($cmd in @("python3", "python")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "(\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 10) {
                $python = $cmd
                break
            }
        }
    } catch {}
}

if (-not $python) {
    Write-Fail "Python 3.10+ is required but not found."
    Write-Host "    Install Python: https://www.python.org/downloads/"
    exit 1
}
Write-Ok "Found $python ($(& $python --version 2>&1))"

# ── Step 2: Virtual environment ──────────────────────────────
Write-Host ""
Write-Host "Step 2/5: Setting up Python virtual environment..."

if (-not (Test-Path ".venv")) {
    & $python -m venv .venv
    Write-Ok "Created virtual environment (.venv\)"
} else {
    Write-Ok "Virtual environment already exists"
}

$venvPython = ".venv\Scripts\python.exe"
$venvPip = ".venv\Scripts\pip.exe"

Write-Info "Installing Python packages (this may take a minute)..."
& $venvPip install -q -r requirements.txt
Write-Ok "Python packages installed"

# ── Step 3: Environment file ─────────────────────────────────
Write-Host ""
Write-Host "Step 3/5: Setting up environment file..."

if (Test-Path ".env") {
    Write-Ok ".env file already exists (skipping)"
    $setupEnv = $false
} else {
    Copy-Item ".env.example" ".env"
    Write-Ok "Created .env from template"
    $setupEnv = $true
}

if ($setupEnv) {
    Write-Host ""
    Write-Host "  Would you like to enter your API keys now?"
    Write-Host "  (You can always edit .env later)"
    Write-Host ""
    $reply = Read-Host "  Set up API keys interactively? [Y/n]"

    if ($reply -ne "n" -and $reply -ne "N") {
        $envContent = Get-Content ".env" -Raw

        # Telegram
        Write-Host ""
        Write-Host "  ── Telegram (for digest delivery) ──" -ForegroundColor Blue
        Write-Host "  Create a bot: message @BotFather on Telegram"
        Write-Host ""
        $tgToken = Read-Host "  Telegram Bot Token (Enter to skip)"
        if ($tgToken) {
            $envContent = $envContent -replace "TELEGRAM_BOT_TOKEN=.*", "TELEGRAM_BOT_TOKEN=$tgToken"
            $tgChat = Read-Host "  Telegram Chat ID"
            if ($tgChat) {
                $envContent = $envContent -replace "TELEGRAM_CHAT_ID=.*", "TELEGRAM_CHAT_ID=$tgChat"
            }
            Write-Ok "Telegram configured"
        } else {
            Write-Warn "Skipped Telegram (use --dry-run to preview digests)"
        }

        # Data sources
        Write-Host ""
        Write-Host "  ── Data Sources (all optional) ──" -ForegroundColor Blue
        Write-Host ""

        $tdKey = Read-Host "  TwelveData key (https://twelvedata.com, Enter to skip)"
        if ($tdKey) {
            $envContent = $envContent -replace "# TWELVEDATA_API_KEY=.*", "TWELVEDATA_API_KEY=$tdKey"
            Write-Ok "TwelveData configured"
        }

        $fhKey = Read-Host "  Finnhub key (https://finnhub.io, Enter to skip)"
        if ($fhKey) {
            $envContent = $envContent -replace "# FINNHUB_API_KEY=.*", "FINNHUB_API_KEY=$fhKey"
            Write-Ok "Finnhub configured"
        }

        $fredKey = Read-Host "  FRED key (https://fred.stlouisfed.org, Enter to skip)"
        if ($fredKey) {
            $envContent = $envContent -replace "# FRED_API_KEY=.*", "FRED_API_KEY=$fredKey"
            Write-Ok "FRED configured"
        }

        $newsKey = Read-Host "  NewsAPI key (https://newsapi.org, Enter to skip)"
        if ($newsKey) {
            $envContent = $envContent -replace "# NEWSAPI_KEY=.*", "NEWSAPI_KEY=$newsKey"
            Write-Ok "NewsAPI configured"
        }

        # LLM
        Write-Host ""
        Write-Host "  ── LLM Provider (optional, adds AI commentary) ──" -ForegroundColor Blue
        Write-Host ""

        $anthKey = Read-Host "  Anthropic key (Enter to skip)"
        if ($anthKey) {
            $envContent = $envContent -replace "# ANTHROPIC_API_KEY=.*", "ANTHROPIC_API_KEY=$anthKey"
            Write-Ok "Anthropic configured"
        }

        $oaiKey = Read-Host "  OpenAI key (Enter to skip)"
        if ($oaiKey) {
            $envContent = $envContent -replace "# OPENAI_API_KEY=.*", "OPENAI_API_KEY=$oaiKey"
            Write-Ok "OpenAI configured"
        }

        $gemKey = Read-Host "  Gemini key (Enter to skip)"
        if ($gemKey) {
            $envContent = $envContent -replace "# GEMINI_API_KEY=.*", "GEMINI_API_KEY=$gemKey"
            Write-Ok "Gemini configured"
        }

        Set-Content ".env" $envContent -NoNewline
    }
}

# ── Step 4: Frontend ──────────────────────────────────────────
Write-Host ""
Write-Host "Step 4/5: Building frontend..."

try {
    $nodeVer = & node --version 2>&1
    Write-Ok "Found Node.js ($nodeVer)"

    Push-Location "ui\frontend"
    if (-not (Test-Path "node_modules")) {
        Write-Info "Installing frontend packages..."
        & npm install --silent
    }
    Write-Info "Building frontend..."
    & npm run build --silent
    Pop-Location
    Write-Ok "Frontend built"
} catch {
    Write-Warn "Node.js not found — skipping frontend build."
    Write-Host "    Install Node.js from https://nodejs.org"
    Write-Host "    Then run: cd ui\frontend && npm install && npm run build"
}

# ── Step 5: Verify ────────────────────────────────────────────
Write-Host ""
Write-Host "Step 5/5: Verifying installation..."

& $venvPython -c "import yfinance, fastapi, yaml; print('All core packages OK')"
Write-Ok "Python packages verified"

# Create runtime directories
New-Item -ItemType Directory -Force -Path "logs\retrace" | Out-Null
New-Item -ItemType Directory -Force -Path "cache" | Out-Null
Write-Ok "Runtime directories ready"

# ── Done ──────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ════════════════════════════════════════════" -ForegroundColor DarkGray
Write-Host ""
Write-Ok "Setup complete!"
Write-Host ""
Write-Host "  Next steps:"
Write-Host ""
Write-Host "    Start the web UI:"
Write-Host "      .venv\Scripts\python scripts\start_ui.py"
Write-Host ""
Write-Host "    Run a digest (preview in terminal):"
Write-Host "      .venv\Scripts\python scripts\run_digest.py --type daytrade --mode facts --dry-run"
Write-Host ""
