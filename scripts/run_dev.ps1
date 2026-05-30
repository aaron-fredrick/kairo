# Native local-dev — hot-reload API (:8000) + Vite (:5173), no Docker.
#   scripts\run_dev.ps1
#   Equivalent to compose profile: local-dev
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path "app_backend\main.py")) {
    Write-Error "Error: run from the kairo project root."
    exit 1
}

if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "Installing frontend dependencies..."
    Push-Location frontend
    npm install --legacy-peer-deps
    Pop-Location
}

if (-not $env:CORS_ORIGINS) {
    $env:CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:8000"
}

Write-Host ""
Write-Host "Native mode (no Docker). Uses .env — defaults: DB_BACKEND=sqlite, EVENT_BUS=local."
Write-Host "For full stack in Docker: scripts\compose\local-dev.bat"
Write-Host ""
Write-Host "API:      http://127.0.0.1:8000  (reload)"
Write-Host "Frontend: http://127.0.0.1:5173  (Vite)"
Write-Host ""

$vite = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory (Resolve-Path "frontend") -PassThru -NoNewWindow

try {
    & python -m uvicorn app_backend.main:app --host 127.0.0.1 --port 8000 --reload --proxy-headers
} finally {
    if (-not $vite.HasExited) { $vite.Kill() }
}
