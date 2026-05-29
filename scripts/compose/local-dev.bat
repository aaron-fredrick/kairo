@echo off
REM Docker: local-dev stack (Caddy :80 + Vite :5173)
cd /d "%~dp0..\.."
docker compose -f compose/base.yml -f compose/app-backend.local-dev.yml up --build %*
