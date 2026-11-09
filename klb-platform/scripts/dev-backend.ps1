# Start the Django development server.
# Run from anywhere: .\scripts\dev-backend.ps1
param(
    [string]$Address = "127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "The virtual environment is missing. Run .\scripts\setup-windows.ps1 first."
}

Set-Location $Backend
& $Python manage.py runserver $Address
