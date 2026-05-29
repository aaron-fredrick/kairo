@echo off
REM Build frontend (if needed), start MinIO, run FastAPI backend only.
setlocal enabledelayedexpansion

cd /d "%~dp0.."
if not exist "app_backend\main.py" (
    echo Error: run from the kairo project root.
    exit /b 1
)

if not exist "app_backend\static\index.html" (
    echo Frontend not built — running build_frontend.bat ...
    call "%~dp0build_frontend.bat"
    if errorlevel 1 exit /b 1
) else (
    echo Using existing app_backend\static\ build ^(delete index.html to force rebuild^).
)

echo Starting MinIO ^(compose infra.minio^)...
docker compose -f compose/infra.minio.yml up -d minio
if errorlevel 1 (
    echo Error: could not start MinIO. Is Docker running?
    exit /b 1
)

echo.
echo MinIO API:     http://127.0.0.1:7000
echo MinIO Console: http://127.0.0.1:7001  ^(username / password from .env^)
echo Backend:       http://127.0.0.1:8000
echo Via Caddy:      http://localhost  ^(use Caddyfile, not Caddyfile.dev^)
echo UPLOAD_BACKEND=minio ^(see .env^)
echo.

python -m uvicorn app_backend.main:app --host 127.0.0.1 --port 8000 --reload --proxy-headers
