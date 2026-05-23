@echo off
REM Start script for FastAPI application in development mode (Windows CMD)

set ENV=development
set DEBUG=true

setlocal enabledelayedexpansion

set PG_UP=true
set REDIS_UP=true

REM Check Postgres
PGPASSWORD=kairo_password psql -h 127.0.0.1 -U kairo -d kairo -c "SELECT 1;" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    psql -U postgres -c "SELECT 1;" >nul 2>&1
    if %ERRORLEVEL% NEQ 0 set PG_UP=false
)

REM Check Redis
set R_STATUS=
for /f "tokens=*" %%i in ('redis-cli -h 127.0.0.1 -p 6379 ping 2^>nul') do set R_STATUS=%%i
if "%R_STATUS%" NEQ "PONG" (
    for /f "tokens=*" %%i in ('redis-cli ping 2^>nul') do set R_STATUS=%%i
)
if "%R_STATUS%" NEQ "PONG" set REDIS_UP=false

if "%PG_UP%"=="false" (
    echo PostgreSQL is down.
)
if "%REDIS_UP%"=="false" (
    echo Redis is down.
)

if "%PG_UP%"=="false" goto :start_services
if "%REDIS_UP%"=="false" goto :start_services
goto :proceed

:start_services
echo Attempting to start services via docker-compose...
if "%PG_UP%"=="false" (
    if "%REDIS_UP%"=="false" (
        docker-compose up -d db redis
    ) else (
        docker-compose up -d db
    )
) else (
    docker-compose up -d redis
)

echo Waiting for services to initialize...
for /L %%i in (1,1,15) do (
    timeout /t 1 >nul
    
    set PG_CHECK=true
    set REDIS_CHECK=true
    
    PGPASSWORD=kairo_password psql -h 127.0.0.1 -U kairo -d kairo -c "SELECT 1;" >nul 2>&1
    if errorlevel 1 (
        psql -U postgres -c "SELECT 1;" >nul 2>&1
        if errorlevel 1 set PG_CHECK=false
    )
    
    set R_CHECK_VAL=
    for /f "tokens=*" %%a in ('redis-cli -h 127.0.0.1 -p 6379 ping 2^>nul') do set R_CHECK_VAL=%%a
    if "!R_CHECK_VAL!" NEQ "PONG" (
        for /f "tokens=*" %%a in ('redis-cli ping 2^>nul') do set R_CHECK_VAL=%%a
    )
    if "!R_CHECK_VAL!" NEQ "PONG" set REDIS_CHECK=false
    
    if "!PG_CHECK!"=="true" if "!REDIS_CHECK!"=="true" (
        goto :proceed
    )
)

:proceed
REM Re-verify before running server
set PG_FINAL=true
set REDIS_FINAL=true

PGPASSWORD=kairo_password psql -h 127.0.0.1 -U kairo -d kairo -c "SELECT 1;" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    psql -U postgres -c "SELECT 1;" >nul 2>&1
    if %ERRORLEVEL% NEQ 0 set PG_FINAL=false
)

set R_FINAL_VAL=
for /f "tokens=*" %%i in ('redis-cli -h 127.0.0.1 -p 6379 ping 2^>nul') do set R_FINAL_VAL=%%i
if "%R_FINAL_VAL%" NEQ "PONG" (
    for /f "tokens=*" %%i in ('redis-cli ping 2^>nul') do set R_FINAL_VAL=%%i
)
if "%R_FINAL_VAL%" NEQ "PONG" set REDIS_FINAL=false

if "%PG_FINAL%"=="false" (
    echo Error: PostgreSQL is not running and could not be started.
    exit /b 1
)

if "%REDIS_FINAL%"=="false" (
    echo Error: Redis is not running and could not be started.
    exit /b 1
)

echo PostgreSQL is up.
echo Redis is up.
echo Starting Kairo development server on http://localhost:8000...
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

