# Secrets

This directory holds sensitive credentials used by the Kairo stack.

## Rules

| Pattern | Tracked by git? |
|---|---|
| `*.txt` | **No** — gitignored. Contains real values for local dev. |
| `*.txt.example` | **Yes** — committed. Contains placeholder values as templates. |

## Setup (first time)

Copy each `.example` file, remove the `.example` suffix, and fill in your values:

```bash
# From the project root
for f in secrets/*.txt.example; do
  dest="${f%.example}"
  [ -f "$dest" ] || cp "$f" "$dest"
done
```

Then edit each `secrets/*.txt` with the real value.

## Secret catalogue

| File | Docker secret name | Used by | Description |
|---|---|---|---|
| `jwt_secret.txt` | `jwt_secret` | API | JWT signing key. Generate: `openssl rand -hex 32` |
| `database_url.txt` | `database_url` | API, workers, WS | Full async DSN: `postgresql+asyncpg://user:pass@host/db` |
| `db_password.txt` | `db_password` | Postgres init | Password for the `kairo` DB user |
| `s3_access_key.txt` | `s3_access_key` | API, blob-worker | S3 / MinIO access key (username) |
| `s3_secret_key.txt` | `s3_secret_key` | API, blob-worker | S3 / MinIO secret key (password) |
| `minio_root_password.txt` | `minio_root_password` | MinIO | MinIO root password — must match `s3_secret_key.txt` |

> **Note:** `db_password.txt` and `database_url.txt` must be consistent —
> the password in the DSN must match the value in `db_password.txt`.

## Docker Swarm

Secrets must be pre-created on the swarm manager before deploying the stack:

```bash
docker secret create jwt_secret          secrets/jwt_secret.txt
docker secret create database_url        secrets/database_url.txt
docker secret create db_password         secrets/db_password.txt
docker secret create s3_access_key       secrets/s3_access_key.txt
docker secret create s3_secret_key       secrets/s3_secret_key.txt
docker secret create minio_root_password secrets/minio_root_password.txt
```

## How secrets are consumed

- **API / workers**: `ConfigResolver` reads `/run/secrets/<name>` at startup.  
  In production (`ENV` unset), secrets are **required** — missing values raise a `RuntimeError`.  
  In development (`.env` present with `ENV=development`), secrets are preferred but env vars are used as fallback.

- **Postgres**: uses the official `POSTGRES_PASSWORD_FILE` env var convention.

- **MinIO**: does not support `_FILE` convention. The compose / swarm entrypoint
  reads the secret file and exports `MINIO_ROOT_PASSWORD` before starting the server.
