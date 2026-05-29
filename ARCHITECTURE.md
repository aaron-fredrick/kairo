# Kairo Architecture

Kairo is a distributed chat system designed for real-time messaging, horizontal scalability, and simplicity.

## High-Level Overview

The system is composed of three primary layers:
1. **Frontend**: A SvelteKit/React application providing the user interface.
2. **Application Server**: A FastAPI Python backend handling REST API requests and WebSocket connections.
3. **Infrastructure**: PostgreSQL for persistent storage and Redis for caching and pub/sub message distribution.

## Components

### 1. Application Server (`app_backend`, FastAPI)
The chat API lives in **`app_backend/`**. It is stateless, allowing multiple instances to run concurrently behind a load balancer (Caddy/Nginx). 

* **REST API**: Handles authentication (`/auth`), room management (`/rooms`), and user queries (`/users`).
* **WebSocket Manager**: Manages active connections. When a message is received, it validates it and publishes it to the Redis Event Bus.

### 2. Event Bus & Cache (Redis)
* **Pub/Sub**: Used to distribute messages across multiple FastAPI nodes. When Node A receives a message, it publishes to a Redis channel. Node B, subscribed to the channel, receives the message and broadcasts it to its connected clients.
* **Presence**: Tracks online users and typing indicators using Redis keys with short TTLs (Time-To-Live).

### 3. Persistent Storage (PostgreSQL)
* **Models**: Stores `Users`, `Rooms`, and `Messages`.
* **Migrations**: Managed via Alembic.
* Acts as the ultimate source of truth for historical message retrieval.

### 4. Register Server (`app_register`, optional, distributed mode)
* **Purpose**: Tracks healthy app server instances and rewrites **Caddy** or **Nginx** upstream configuration.
* **Registration**: Each app node calls `POST /api/v1/register` on startup with HMAC auth (`REGISTER_SYSTEM_KEY`).
* **Heartbeats**: Periodic `POST /api/v1/heartbeat/{server_id}` using a per-server secret; stale nodes are removed from the load balancer.
* **Shared state**: App nodes still require shared **PostgreSQL**, **Redis**, and **MinIO/S3** for data and blobs.
* **Architecture**: Layered design (domain → ports → adapters → coordinator → API). See [app_register/ARCHITECTURE.md](app_register/ARCHITECTURE.md) for flows, security, and extension points.

## Data Flow

1. **Client connects** via WebSocket to `Node A`.
2. **Client sends message** -> `Node A` validates the session.
3. `Node A` saves the message to **PostgreSQL**.
4. `Node A` publishes the message event to **Redis**.
5. `Node A` and `Node B` (and any other nodes) receive the event from **Redis**.
6. Nodes broadcast the message to their respective connected clients.
