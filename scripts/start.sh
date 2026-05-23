#!/bin/bash
# Start script for FastAPI application in development mode

export ENV=development
export DEBUG=true

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

check_postgres || PG_UP=false
check_redis || REDIS_UP=false

if [ "$PG_UP" = false ] || [ "$REDIS_UP" = false ]; then
    echo "Required services (Postgres and/or Redis) are not running locally."
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
        check_postgres && PG_UP=true
        check_redis && REDIS_UP=true
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

echo "PostgreSQL is up."
echo "Redis is up."
echo "Starting Kairo development server on http://localhost:8000..."
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
