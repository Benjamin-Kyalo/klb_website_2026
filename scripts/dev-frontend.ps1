# Start the Vite development server.
# Run from anywhere: .\scripts\dev-frontend.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "frontend"

if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    throw "Frontend dependencies are missing. Run .\scripts\setup-windows.ps1 first."
}

Set-Location $Frontend
npm run dev
