# Quick project sanity check (no full CI suite).
#   .\scripts\check.ps1
#   .\scripts\check.ps1 -Full
#   .\scripts\check.ps1 -Http
param(
    [switch]$Full,
    [switch]$Http
)

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "==> Python import check"
python -c "import src.backend.main; import src.register.main; print('ok: backend, register')"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "==> Pytest (quick)"
if ($Full) {
    python -m pytest tests/backend tests/register tests/shared `
        -m "unit or component or smoke" -q --tb=line
} else {
    python -m pytest tests/backend/smoke tests/shared/unit tests/register/unit `
        -q --tb=line
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($Http) {
    Write-Host ""
    Write-Host "==> HTTP (Caddy :80, if running)"
    try {
        $null = Invoke-WebRequest -Uri "http://127.0.0.1/openapi.json" -UseBasicParsing -TimeoutSec 3
        Write-Host "ok: http://127.0.0.1/openapi.json"
        $r = Invoke-WebRequest -Uri "http://127.0.0.1/auth/join" -Method POST `
            -ContentType "application/json" -Body "{}" -UseBasicParsing -TimeoutSec 3
        Write-Host "guest join: HTTP $($r.StatusCode)"
    } catch {
        Write-Host "skip: nothing on http://127.0.0.1 (start stack: .\scripts\compose-up.ps1 local)"
    }
}

Write-Host ""
Write-Host "==> Done"
