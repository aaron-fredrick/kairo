# Native local — built frontend served by API on :8000 (no Docker).
#   scripts\run.ps1
#   Equivalent to compose profile: local
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path "src\backend\main.py")) {
    Write-Error "Error: run from the kairo project root."
    exit 1
}

if (-not (Test-Path "src\backend\static\index.html")) {
    Write-Host "Building frontend into src\backend\static\ ..."
    Push-Location src\frontend
    npm install --legacy-peer-deps
    npm run build
    Pop-Location
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host ""
Write-Host "Native mode (no Docker). Uses .env — defaults: DB_BACKEND=sqlite, EVENT_BUS=local."
Write-Host "For full stack in Docker: scripts\compose\local.bat"
Write-Host ""
Write-Host "Open http://127.0.0.1:8000"
Write-Host ""

& python -m uvicorn src.backend.main:app --host 127.0.0.1 --port 8000 --proxy-headers
