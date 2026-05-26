@echo off
REM Start script for FastAPI application in development mode (Windows CMD)

set ENV=development
set DEBUG=true
setlocal enabledelayedexpansion

set DB_BACKEND=postgres
set EVENT_BUS=local

if exist .env (
    for /f "tokens=1,2 delims==" %%A in (.env) do (
        if "%%A"=="DB_BACKEND" set DB_BACKEND=%%B
        if "%%A"=="EVENT_BUS" set EVENT_BUS=%%B
    )
)

set PG_UP=true
set REDIS_UP=true

if "!DB_BACKEND!" NEQ "sqlite" (
    REM Check Postgres
    set PG_UP=false
    PGPASSWORD=kairo_password psql -h 127.0.0.1 -U kairo -d kairo -c "SELECT 1;" >nul 2>&1
    if !ERRORLEVEL! EQU 0 set PG_UP=true
    if "!PG_UP!"=="false" (
        psql -U postgres -c "SELECT 1;" >nul 2>&1
        if !ERRORLEVEL! EQU 0 set PG_UP=true
    )
)

if "!EVENT_BUS!" EQU "redis" (
    REM Check Redis
    set REDIS_UP=false
    set R_STATUS=
    for /f "tokens=*" %%i in ('redis-cli -h 127.0.0.1 -p 6379 ping 2^>nul') do set R_STATUS=%%i
    if "!R_STATUS!" EQU "PONG" set REDIS_UP=true
    if "!REDIS_UP!"=="false" (
        set R_STATUS=
        for /f "tokens=*" %%i in ('redis-cli ping 2^>nul') do set R_STATUS=%%i
        if "!R_STATUS!" EQU "PONG" set REDIS_UP=true
    )
)

if "!PG_UP!"=="false" goto :start_services
if "!REDIS_UP!"=="false" goto :start_services
goto :proceed

:start_services
echo Attempting to start missing services via docker-compose...
if "!PG_UP!"=="false" (
    if "!REDIS_UP!"=="false" (
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
    
    if "!DB_BACKEND!" NEQ "sqlite" (
        set PG_UP=false
        PGPASSWORD=kairo_password psql -h 127.0.0.1 -U kairo -d kairo -c "SELECT 1;" >nul 2>&1
        if !ERRORLEVEL! EQU 0 set PG_UP=true
        if "!PG_UP!"=="false" (
            psql -U postgres -c "SELECT 1;" >nul 2>&1
            if !ERRORLEVEL! EQU 0 set PG_UP=true
        )
    )
    
    if "!EVENT_BUS!" EQU "redis" (
        set REDIS_UP=false
        set R_STATUS=
        for /f "tokens=*" %%a in ('redis-cli -h 127.0.0.1 -p 6379 ping 2^>nul') do set R_STATUS=%%a
        if "!R_STATUS!" EQU "PONG" set REDIS_UP=true
        if "!REDIS_UP!"=="false" (
            set R_STATUS=
            for /f "tokens=*" %%a in ('redis-cli ping 2^>nul') do set R_STATUS=%%a
            if "!R_STATUS!" EQU "PONG" set REDIS_UP=true
        )
    )
    
    if "!PG_UP!"=="true" if "!REDIS_UP!"=="true" goto :proceed
)

:proceed
if "!PG_UP!"=="false" (
    echo Error: PostgreSQL is not running and could not be started.
    exit /b 1
)

if "!REDIS_UP!"=="false" (
    echo Error: Redis is not running and could not be started.
    exit /b 1
)

echo Services are up.
echo Starting Kairo development server on http://localhost:8000...
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --proxy-headers
