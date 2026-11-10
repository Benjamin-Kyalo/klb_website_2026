# Set up the KLB website on Windows.
# Usage:
#   .\scripts\setup-windows.ps1
#   .\scripts\setup-windows.ps1 -SkipBuild     # skip the production frontend build
param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

function Require-Command {
    param([string]$Name, [string]$Message)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name was not found. $Message"
    }
}

Write-Host "KLB website setup" -ForegroundColor Cyan
Write-Host "Project: $Root"

Require-Command "python" "Install Python 3.11 or newer and add it to PATH."
Require-Command "node" "Install Node.js 20 or newer."
Require-Command "npm" "Install Node.js 20 or newer (npm is included)."

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------
Set-Location $Backend

if (-not (Test-Path $Python)) {
    Write-Host "Creating the Python virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
}

Write-Host "Installing backend dependencies..." -ForegroundColor Cyan
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt

$EnvFile = Join-Path $Backend ".env"
if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $Backend ".env.example") $EnvFile
    Write-Host ""
    Write-Host "Created backend\.env from .env.example." -ForegroundColor Yellow
    Write-Host "Edit backend\.env now and set:" -ForegroundColor Yellow
    Write-Host "  DJANGO_SECRET_KEY, DATABASE_URL, SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD"
    Write-Host "Then run this script again." -ForegroundColor Yellow
    Set-Location $Root
    exit 1
}

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------
Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
Set-Location $Frontend
npm install

# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------
# This script uses the PostgreSQL server already installed on this computer.
# Create the user and database first (see docs/SETUP.md step 3), then set
# DATABASE_URL in backend/.env.

# Wait for the database using the connection string in backend/.env.
Write-Host "Waiting for the database..." -ForegroundColor Cyan
Set-Location $Backend
$WaitScript = @'
import os
import time

import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL is not set in backend/.env")

last_error = None
for _ in range(15):
    try:
        with psycopg.connect(url, connect_timeout=3):
            print("Database is ready.")
            raise SystemExit(0)
    except Exception as exc:
        last_error = exc
        time.sleep(2)

print("The database did not become ready.")
print(f"Last error: {last_error}")
print("Check that the PostgreSQL service is running (services.msc).")
print("Create the user and database first - see docs/SETUP.md step 3.")
print("Then check DATABASE_URL in backend/.env.")
raise SystemExit(1)
'@
$WaitScript | & $Python -
if ($LASTEXITCODE -ne 0) {
    throw "Could not connect to PostgreSQL."
}

# ---------------------------------------------------------------------------
# Tables and content
# ---------------------------------------------------------------------------
Write-Host "Applying migrations..." -ForegroundColor Cyan
& $Python manage.py migrate
if ($LASTEXITCODE -ne 0) { throw "Migrations failed." }

Write-Host "Seeding pages, books and settings..." -ForegroundColor Cyan
& $Python manage.py seed_content
if ($LASTEXITCODE -ne 0) { throw "Content seeding failed." }

# ---------------------------------------------------------------------------
# Production bundle
# ---------------------------------------------------------------------------
if (-not $SkipBuild) {
    Write-Host "Building the frontend..." -ForegroundColor Cyan
    Set-Location $Frontend
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }

    Write-Host "Collecting Django static files..." -ForegroundColor Cyan
    Set-Location $Backend
    & $Python manage.py collectstatic --noinput
    if ($LASTEXITCODE -ne 0) { throw "collectstatic failed." }
}

Set-Location $Root

Write-Host ""
Write-Host "Setup finished." -ForegroundColor Green
Write-Host "Start the backend:  .\scripts\dev-backend.ps1"
Write-Host "Start the frontend: .\scripts\dev-frontend.ps1"
Write-Host "Then open http://localhost:5173 and sign in at /admin"
Write-Host "Use the SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD from backend\.env."
