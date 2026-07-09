# setup.ps1 - LearnStack local dev setup
# Run from the repo root: .\setup.ps1
#
# What this does:
#   1. Start Docker containers (Postgres with pgvector)
#   2. Create and activate a Python virtual environment
#   3. Install dependencies
#   4. Copy .env.example to .env if not already present (then pause for key entry)
#   5. Run Alembic migrations
#   6. Create the test database (one-time, safe to re-run)
#   7. Start the FastAPI dev server

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host ">> $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "   $Message" -ForegroundColor Green
}

function Write-Note {
    param([string]$Message)
    Write-Host "   $Message" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Step 1 - Docker
# ---------------------------------------------------------------------------
Write-Step "Starting Docker containers..."

$ErrorActionPreference = "SilentlyContinue"
docker info 2>$null | Out-Null
$dockerOk = $LASTEXITCODE -eq 0
$ErrorActionPreference = "Stop"

if (-not $dockerOk) {
    Write-Host "ERROR: Docker is not running. Start Docker Desktop and re-run this script." -ForegroundColor Red
    exit 1
}

docker compose up -d
Write-Success "Containers started."

# Wait for Postgres to be ready before continuing
Write-Step "Waiting for Postgres to be ready..."
$maxAttempts = 30
$attempt = 0
do {
    $attempt++
    docker compose exec -T db pg_isready -U postgres 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { break }
    if ($attempt -ge $maxAttempts) {
        Write-Host "ERROR: Postgres did not become ready in time." -ForegroundColor Red
        exit 1
    }
    Start-Sleep -Seconds 2
} while ($true)
Write-Success "Postgres is ready."

# ---------------------------------------------------------------------------
# Step 2 - Virtual environment
# ---------------------------------------------------------------------------
Write-Step "Setting up Python virtual environment..."

if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Success "Created .venv"
} else {
    Write-Note ".venv already exists - skipping creation."
}

& .\.venv\Scripts\Activate.ps1
Write-Success "Virtual environment activated."

# ---------------------------------------------------------------------------
# Step 3 - Dependencies
# ---------------------------------------------------------------------------
Write-Step "Installing dependencies..."
pip install -r requirements.txt --quiet
Write-Success "Dependencies installed."

# ---------------------------------------------------------------------------
# Step 4 - .env file
# ---------------------------------------------------------------------------
Write-Step "Checking .env file..."

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ""
    Write-Host "   .env created from .env.example." -ForegroundColor Yellow
    Write-Host "   ACTION REQUIRED: open .env and fill in these values before continuing:" -ForegroundColor Yellow
    Write-Host "     OPENAI_API_KEY       - required for embedding pipeline" -ForegroundColor Yellow
    Write-Host "     ANTHROPIC_API_KEY    - required for /ask and /draft endpoints" -ForegroundColor Yellow
    Write-Host "     BASIC_AUTH_USERNAME  - required; every route except /health 401s without it" -ForegroundColor Yellow
    Write-Host "     BASIC_AUTH_PASSWORD  - required; pick any values for local dev" -ForegroundColor Yellow
    Write-Host "     POSTGRES_PASSWORD    - change from default if needed" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Re-run .\setup.ps1 after saving .env." -ForegroundColor Yellow
    exit 0
} else {
    Write-Note ".env already exists - skipping copy."
}

# ---------------------------------------------------------------------------
# Step 5 - Alembic migrations
# ---------------------------------------------------------------------------
Write-Step "Running Alembic migrations..."
alembic upgrade head
Write-Success "Migrations applied."

# ---------------------------------------------------------------------------
# Step 6 - Test database (one-time setup, safe to re-run)
# ---------------------------------------------------------------------------
Write-Step "Ensuring test database exists..."

$pgUser = "postgres"
$envContent = Get-Content ".env" -ErrorAction SilentlyContinue
foreach ($line in $envContent) {
    if ($line -match "^POSTGRES_USER=(.+)$") {
        $pgUser = $Matches[1].Trim()
    }
}

$ErrorActionPreference = "SilentlyContinue"
docker compose exec -T db psql -U $pgUser -c "CREATE DATABASE learnstack_test;" 2>$null | Out-Null
docker compose exec -T db psql -U $pgUser -d learnstack_test -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>$null | Out-Null
$ErrorActionPreference = "Stop"
Write-Success "Test database ready."

# ---------------------------------------------------------------------------
# Step 7 - Start the dev server
# ---------------------------------------------------------------------------
Write-Step "Starting FastAPI dev server..."
Write-Host ""
Write-Host "   Web UI:   http://localhost:8000/" -ForegroundColor Green
Write-Host "   API docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "   Press Ctrl+C to stop the server." -ForegroundColor Yellow
Write-Host ""

uvicorn app.main:app --reload
