@echo off
REM Docker: app-register + dynamic Caddy
cd /d "%~dp0..\.."
docker compose -f compose/base.yml -f compose/app-register.yml up --build %*
