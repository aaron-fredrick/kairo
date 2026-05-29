@echo off
set PROFILE=%~1
if "%PROFILE%"=="" set PROFILE=local
shift
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0compose-ps.ps1" %PROFILE% %*
