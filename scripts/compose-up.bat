@echo off
if "%~1"=="" (
    echo Usage: compose-up.bat PROFILE [docker compose args]
    echo Profiles: local, local-dev, standalone, register, workers, distributed, minio, ...
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0compose-up.ps1" %*
