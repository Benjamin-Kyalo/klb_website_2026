# Start the Django development server against a local database.
# Run from anywhere: .\scripts\dev-backend.ps1
#
# The development settings refuse to start against Supabase, so a local
# DATABASE_URL is required. Pass it explicitly or export it first:
#   .\scripts\dev-backend.ps1 -DatabaseUrl "postgres://postgres:1234@127.0.0.1:5432/klb_verify"
param(
    [string]$Address = "127.0.0.1:8000",
    [string]$DatabaseUrl = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "The virtual environment is missing. Run .\scripts\setup-windows.ps1 first."
}

if ($DatabaseUrl) {
    $env:DATABASE_URL = $DatabaseUrl
}

Set-Location $Backend
& $Python manage.py runserver $Address --settings=config.dev_settings
