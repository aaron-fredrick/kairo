@echo off
REM Docker: standalone cluster (scale with --scale app-backend=2)
cd /d "%~dp0..\.."
docker compose -f compose/base.yml -f compose/app-backend.standalone.yml up --build %*
