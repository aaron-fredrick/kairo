@echo off
REM Docker: app-backend workers (use with register stack)
cd /d "%~dp0..\.."
docker compose -f compose/base.yml -f compose/app-backend.workers.yml up --build %*
