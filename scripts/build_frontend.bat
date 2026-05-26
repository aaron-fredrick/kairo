@echo off
REM Build script for the Kairo frontend Svelte application (Windows CMD)

echo Building Kairo frontend...

REM Ensure we are in the project root
if not exist "frontend\" (
    echo Error: frontend directory not found. Run this from the project root.
    exit /b 1
)

cd frontend || exit /b 1

echo Installing npm dependencies...
call npm install

echo Compiling static assets...
call npm run build

echo Frontend build complete! Static files have been placed in app/static/
