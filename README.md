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
- `/app` - Backend FastAPI application containing endpoints, models, services, database configurations, and WS managers.
- `/frontend` - Frontend application source (Svelte/React).
- `/infra` - Docker Compose and Nginx configuration templates.
- `/scripts` - Automation scripts for server startup, database migrations, and database seeding.

## Setup & Running

### Prerequisites
- Python 3.10+
- Node.js 18+ (for local frontend development)
- PostgreSQL & Redis (running locally or via Docker)

### Run Locally (Without Containers)

1. **Install Python Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment:**
   Create a `.env` file from the placeholder (or use the preconfigured one):
   ```bash
   cp .env.example .env  # Or edit the created .env
   ```

3. **Start backend server:**
   - On Linux/macOS:
     ```bash
     ./scripts/start.sh
     ```
   - On Windows:
     ```cmd
     .\scripts\start.bat
     ```

4. **Install & Run Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### Run With Docker Compose
```bash
docker-compose up --build
```
