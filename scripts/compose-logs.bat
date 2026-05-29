@echo off
if "%~1"=="" (
    echo Usage: compose-logs.bat PROFILE [service] [-f]
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0compose-logs.ps1" %*
