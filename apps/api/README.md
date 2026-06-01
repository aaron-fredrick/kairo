# Kairo API Microservice

This is the main API microservice for the Kairo project.

## Architecture
- **Framework:** FastAPI
- **Database:** PostgreSQL (with `asyncpg`)
- **Event Bus & Caching:** Redis
- **Storage:** S3 / Minio
- **Pattern:** Controller -> Mediator -> Repository

## Features
- **Authentication:** In-house JWT authentication at `/api/auth` (login, register, me). Security dependencies parse and validate access tokens directly.
- **File Uploads:** Uploads are written to a `temp/` prefix in the storage system and pushed to a Redis queue for processing by a worker service.
- **Idempotency:** Implemented for key operations including file uploads using the `Idempotency-Key` header.
- **Resilience:** Implements retry logic on startup and runtime for Database, Redis, and Storage connections.
- **Observability:** Centralized logging, Prometheus metrics, and OpenTelemetry tracing built-in.
- **Presence Tracking:** Heartbeat system with eventual consistency backed by Redis sorted sets.
- **Access Control:** Role-based access control with specific roles.

## Running Locally

To run locally without Docker:
```bash
uvicorn app.main:app --reload --port 8000
```

## Docker

Build the Docker image from the project root:
```bash
docker build -t kairo-api -f apps/api/Dockerfile .
```

Run the container:
```bash
docker run -p 8000:8000 --env-file .env kairo-api
```
