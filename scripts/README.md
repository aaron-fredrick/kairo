# Scripts

Run from the **repository root** (scripts `cd` to root automatically).

## Native run (no Docker)

| Script | Same as compose profile | What you get |
|--------|-------------------------|--------------|
| **`run.sh`** / **`run.ps1`** / **`run.bat`** | `local` | Built UI served by API — **http://127.0.0.1:8000** |
| **`run_dev.sh`** / **`run_dev.ps1`** / **`run_dev.bat`** | `local-dev` | API hot-reload `:8000` + Vite **http://127.0.0.1:5173** |

Uses `.env` (defaults: `DB_BACKEND=sqlite`, `EVENT_BUS=local`). No containers started.

```bash
# Linux / macOS
./scripts/run.sh
./scripts/run_dev.sh

# PowerShell
.\scripts\run.ps1
.\scripts\run_dev.ps1

# CMD
scripts\run.bat
scripts\run_dev.bat
```

## Docker Compose

Docker equivalents live under **`scripts/compose/`**:

| Native | Docker equivalent |
|--------|-------------------|
| `run` | `compose/local.sh` or `compose\local.bat` |
| `run_dev` | `compose/local-dev.sh` or `compose\local-dev.bat` |

Generic helpers (`.sh`, `.ps1`, `.bat`):

| Script | Action |
|--------|--------|
| `compose-up` | `up --build` |
| `compose-down` | `down` |
| `compose-ps` | `ps` |
| `compose-logs` | `logs` |

Profiles: `local`, `local-dev`, `standalone`, `register`, `workers`, `distributed`, `minio`, `postgresql`, `redis`.

```bash
./scripts/compose/local.sh
scripts\compose\local-dev.bat
scripts\compose-up.bat distributed --scale app-backend=2
```

After Docker **local** / **local-dev**: **http://127.0.0.1** (Caddy). Native **run_dev** uses Vite on **:5173** directly.

## Quick check

| Script | Description |
|--------|-------------|
| `check.sh` / `check.ps1` / **`check.bat`** | Imports + fast pytest |
| `check --full` / `-Full` | Broader test set |
| `check --http` / `-Http` | Probe Caddy on `:80` if up |

## Other

| Script | Description |
|--------|-------------|
| `migrate.sh` | Run Alembic DB migrations |
| `seed.py` | Seed the database with initial data |

See [compose/README.md](../compose/README.md) for stack files.
