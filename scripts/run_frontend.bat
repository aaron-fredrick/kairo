@echo off
REM Script to run the Kairo frontend development server (Windows CMD)

echo Starting Kairo frontend standalone dev server...

REM Ensure we are in the project root
if not exist "frontend\" (
    echo Error: frontend directory not found. Run this from the project root.
    exit /b 1
)

cd frontend || exit /b 1

REM Install dependencies if node_modules doesn't exist
if not exist "node_modules\" (
    echo First time setup: Installing npm dependencies...
    call npm install --legacy-peer-deps
)

echo Launching Vite dev server on http://localhost:5173...
call npm run dev
