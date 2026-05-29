# Kairo

Kairo is a self-hosted, distributed real-time communication platform built for speed and modularity. It supports room/channel-based chat, persistent message history, and horizontal scaling via a shared Redis event bus.

## Features
- **Realtime Messaging**: WebSocket connections with low latency.
- **Stateless App Nodes**: Horizontally scalable FastAPI app instances.
- **Event Bus & Presence**: Redis Pub/Sub coordinates events between nodes; stores active user presence and typing indicators.
- **Persistent Storage**: PostgreSQL database for rooms, messages, and user records.
- **Anonymous Username Generation**: Automatic `adjective-noun` formatting for anonymous guests.

## Architecture

```
                                  +-------------------+
                                  |   Web Client      |
                                  +---------+---------+
                                            | (HTTP/WS)
                                            v
                                  +---------+---------+
                                  |   FastAPI Node    |
                                  +---+-----------+---+
                                      |           |
               +----------------------+           +----------------------+
               | (SQL / AsyncPG)                                         | (Pub/Sub & Cache)
               v                                                         v
    +----------+----------+                                   +----------+----------+
    |     PostgreSQL      |                                   |        Redis        |
    | (Persistent Storage)|                                   | (Event Bus/Presence)|
    +---------------------+                                   +---------------------+
```

## Structure
- `/app_backend` — Chat API (FastAPI): endpoints, models, services, WebSockets, storage.
- `/app_register` — Service registry and dynamic Caddy/Nginx config (distributed deployments).
- `/shared` — Cross-service utilities (e.g. HMAC auth).
- `/frontend` — Frontend application source (Svelte/React).
- `/infra` - Docker Compose and Nginx configuration templates.
- `/scripts` - Automation scripts for server startup, database migrations, and database seeding.

## Setup & Running

### Prerequisites
- Python 3.10+
- Node.js 18+ (for local frontend development)
- PostgreSQL & Redis (running locally or via Docker)

### Run locally (no Docker)

Install deps once: `pip install -r requirements.txt`, copy `.env.example` → `.env`.

**`run`** = local profile on the host (built UI + API):

```bash
./scripts/run.sh          # Linux/macOS
scripts\run.bat           # Windows
```

Open **http://127.0.0.1:8000**. Uses `.env` (sqlite + local event bus by default).

**`run_dev`** = local-dev on the host (API reload + Vite):

```bash
./scripts/run_dev.sh
scripts\run_dev.bat
```

API **http://127.0.0.1:8000**, frontend **http://127.0.0.1:5173**.

### Run with Docker

Same profiles, in containers (Postgres, Redis, MinIO, Caddy):

```bash
scripts\compose\local.bat
scripts\compose\local-dev.bat
./scripts/compose/distributed.sh --scale app-backend=2
```

Open **http://127.0.0.1** (Caddy). See [scripts/README.md](scripts/README.md).

### Quick check

```bash
./scripts/check.sh
scripts\check.bat
```
