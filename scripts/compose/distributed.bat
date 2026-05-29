@echo off
REM Docker: full distributed stack
cd /d "%~dp0..\.."
docker compose -f compose/stack.distributed.yml up --build %*
