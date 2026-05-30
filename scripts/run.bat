@echo off
REM Native local — built frontend served by API on :8000 (no Docker).
REM   scripts\run.bat
setlocal
cd /d "%~dp0.."

if not exist "app_backend\main.py" (
    echo Error: run from the kairo project root.
    exit /b 1
)

if not exist "app_backend\static\index.html" (
    echo Building frontend into app_backend\static\ ...
    pushd frontend
    call npm install --legacy-peer-deps
    call npm run build
    popd
    if errorlevel 1 exit /b 1
)

echo.
echo Native mode (no Docker). Uses .env — defaults: DB_BACKEND=sqlite, EVENT_BUS=local.
echo For full stack in Docker: scripts\compose\local.bat
echo.
echo Open http://127.0.0.1:8000
echo.

python -m uvicorn app_backend.main:app --host 127.0.0.1 --port 8000 --proxy-headers
