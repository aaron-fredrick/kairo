# Kairo — Compose Variants

All compose files live here. Run them from the **project root** so relative
paths to `../../.env` and `../../secrets/` resolve correctly.

## Environment detection

| Condition | `ENV` value | ConfigResolver mode |
|---|---|---|
| `.env` present (contains `ENV=development`) | `development` | Secrets → env vars → defaults |
| `.env` absent | unset | **Production** — secrets required, no fallback |

## Variant matrix

| File | Image source | Infra included | Use case |
|---|---|---|---|
| `docker-compose.local.yml` | pulls `ghcr.io/…` | postgres + redis + minio | Full local stack, no source needed |
| `docker-compose.local.test.yml` | builds from source | postgres + redis + minio | Hot-reload dev / running tests locally |
| `docker-compose.api.yml` | pulls `ghcr.io/…` | — | API only; infra managed externally |
| `docker-compose.api.test.yml` | builds from source | — | API hot-reload; infra managed externally |

## Quick start

```bash
# Full local stack — pull images (development mode via .env)
docker compose -f infra/compose/docker-compose.local.yml up -d

# Full local stack — build from source with hot-reload
docker compose -f infra/compose/docker-compose.local.test.yml up -d

# API only — pull image (point DB_HOST / REDIS_HOST / MINIO_ENDPOINT via .env)
docker compose -f infra/compose/docker-compose.api.yml up -d

# API only — build from source
docker compose -f infra/compose/docker-compose.api.test.yml up -d
```

## Secrets prerequisite

All variants expect `secrets/*.txt` to be populated.
See [secrets/README.md](../../secrets/README.md) for setup instructions.

## Ports

| Service | Host port | Notes |
|---|---|---|
| API | `8000` | Configurable via `API_PORT` |
| MinIO S3 | `7000` | Maps to container port `9000` |
| MinIO console | `7001` | Maps to container port `9001` |
| Postgres | not exposed | Internal network only |
| Redis | not exposed | Internal network only |
