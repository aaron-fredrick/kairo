#!/bin/bash
# Start script for FastAPI application in development mode

export ENV=development
export DEBUG=true

# Load .env variables if present
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

DB_BACKEND=${DB_BACKEND:-postgres}
EVENT_BUS=${EVENT_BUS:-local}

check_postgres() {
    PGPASSWORD=kairo_password psql -h 127.0.0.1 -U kairo -d kairo -c "SELECT 1;" >/dev/null 2>&1 || \
    psql -U postgres -c "SELECT 1;" >/dev/null 2>&1
}

check_redis() {
    [ "$(redis-cli -h 127.0.0.1 -p 6379 ping 2>/dev/null)" = "PONG" ] || \
    [ "$(redis-cli ping 2>/dev/null)" = "PONG" ]
}

PG_UP=true
REDIS_UP=true

if [ "$DB_BACKEND" != "sqlite" ]; then
    check_postgres || PG_UP=false
fi

if [ "$EVENT_BUS" == "redis" ]; then
    check_redis || REDIS_UP=false
fi

if [ "$PG_UP" = false ] || [ "$REDIS_UP" = false ]; then
    echo "Required services are not running locally."
    echo "Attempting to start them via docker-compose..."
    
    if [ "$PG_UP" = false ] && [ "$REDIS_UP" = false ]; then
        docker-compose up -d db redis
    elif [ "$PG_UP" = false ]; then
        docker-compose up -d db
    else
        docker-compose up -d redis
    fi
    
    echo "Waiting for services to initialize..."
    for i in {1..15}; do
        sleep 1
        
        if [ "$DB_BACKEND" != "sqlite" ]; then
            check_postgres && PG_UP=true
        fi
        
        if [ "$EVENT_BUS" == "redis" ]; then
            check_redis && REDIS_UP=true
        fi
        
        if [ "$PG_UP" = true ] && [ "$REDIS_UP" = true ]; then
            break
        fi
    done
fi

if [ "$PG_UP" = false ]; then
    echo "Error: PostgreSQL is not running and could not be started."
    exit 1
fi

if [ "$REDIS_UP" = false ]; then
    echo "Error: Redis is not running and could not be started."
    exit 1
fi

echo "Services are up."
echo "Starting Kairo development server on http://localhost:8000..."
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --proxy-headers --forwarded-allow-ips "*"
