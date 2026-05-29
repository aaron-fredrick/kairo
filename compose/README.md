# Docker Compose profiles

Combine **`base.yml`** (PostgreSQL, Redis, MinIO) with an overlay, or use a stack file.

```bash
# From repository root
docker compose -f compose/base.yml -f compose/app-backend.local.yml up --build

# Or native (no Docker): scripts/run.sh and scripts/run_dev.sh — see scripts/README.md
./scripts/compose-up.sh local
./scripts/compose/local-dev.sh
.\scripts\compose\local.ps1
```

## Files

| File | Purpose |
|------|---------|
| `base.yml` | Shared data plane: postgres, redis, minio, minio-init |
| `app-backend.local.yml` | Single **app-backend** + Caddy `:80` (built frontend in image) |
| `app-backend.local-dev.yml` | **app-backend** `--reload`, Vite `:5173`, Caddy `:80` |
| `app-backend.standalone.yml` | Cluster without register; `--scale app-backend=3` |
| `app-backend.workers.yml` | **app-backend** nodes that register with **app-register** |
| `app-register.yml` | **app-register** + Caddy (auto-generated upstreams) |
| `stack.distributed.yml` | `base` + `app-register` + `app-backend.workers` (one command) |
| `infra.minio.yml` | MinIO + Caddy only |
| `infra.postgresql.yml` | PostgreSQL on host `:5432` |
| `infra.redis.yml` | Redis on host `:6379` |

## Service names

Docker Compose services use **`app-backend`** and **`app-register`** (DNS names on the `kairo` network). Example: `REGISTER_URL=http://app-register:8100`.

## Distributed layout

```bash
# Terminal 1 — register + edge proxy
export REGISTER_SYSTEM_KEY=your-shared-secret
docker compose -f compose/base.yml -f compose/app-register.yml up --build

# Terminal 2 — backend workers
docker compose -f compose/base.yml -f compose/app-backend.workers.yml up --build --scale app-backend=2

# Or all-in-one:
docker compose -f compose/stack.distributed.yml up --build --scale app-backend=2
```

See [app_register/ARCHITECTURE.md](../app_register/ARCHITECTURE.md) for the register service design.

## Security

Set the same **`REGISTER_SYSTEM_KEY`** on **app-register** and all **app-backend** nodes. Registration uses HMAC-SHA256 (`X-Kairo-Timestamp`, `X-Kairo-Signature`). Heartbeats use a per-server secret from registration.

## Proxy type

**app-register** supports **`PROXY_TYPE=caddy`** (default) or **`nginx`**. For Caddy in Compose, use `PROXY_RELOAD_COMMAND=""` and `caddy run --watch`.
