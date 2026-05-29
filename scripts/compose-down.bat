@echo off
set PROFILE=%~1
if "%PROFILE%"=="" set PROFILE=local
shift
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0compose-down.ps1" %PROFILE% %*
