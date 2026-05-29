@echo off
REM Docker: local stack (Caddy http://127.0.0.1)
cd /d "%~dp0..\.."
docker compose -f compose/base.yml -f compose/app-backend.local.yml up --build %*
