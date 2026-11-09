# Build the production frontend and collect Django static files.
# Usage: .\scripts\build.ps1
param(
    [string]$SiteUrl = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "The virtual environment is missing. Run .\scripts\setup-windows.ps1 first."
}

if ($SiteUrl) {
    $env:VITE_SITE_URL = $SiteUrl
    Write-Host "Building with VITE_SITE_URL=$SiteUrl" -ForegroundColor Cyan
}

Set-Location $Frontend
if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    npm install
}
npm run build
if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }

Set-Location $Backend
& $Python manage.py collectstatic --noinput
if ($LASTEXITCODE -ne 0) { throw "collectstatic failed." }

Write-Host "Build complete." -ForegroundColor Green
Write-Host "The built site is served by Django from frontend\dist."
