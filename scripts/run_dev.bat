@echo off
REM Native local-dev — hot-reload API (:8000) + Vite (:5173), no Docker.
REM   scripts\run_dev.bat
setlocal
cd /d "%~dp0.."

if not exist "app_backend\main.py" (
    echo Error: run from the kairo project root.
    exit /b 1
)

if not exist "frontend\node_modules\" (
    echo Installing frontend dependencies...
    pushd frontend
    call npm install --legacy-peer-deps
    popd
)

echo.
echo Native mode (no Docker). Uses .env — defaults: DB_BACKEND=sqlite, EVENT_BUS=local.
echo For full stack in Docker: scripts\compose\local-dev.bat
echo.
echo API:      http://127.0.0.1:8000  (reload)
echo Frontend: http://127.0.0.1:5173  (Vite)
echo.

if not defined CORS_ORIGINS set CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:8000

start "Kairo Vite" cmd /k "cd /d %CD%\frontend && npm run dev"

python -m uvicorn app_backend.main:app --host 127.0.0.1 --port 8000 --reload --proxy-headers
