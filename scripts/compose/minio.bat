@echo off
REM Docker: MinIO only
cd /d "%~dp0..\.."
docker compose -f compose/infra.minio.yml up --build %*
