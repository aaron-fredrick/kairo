#!/usr/bin/env bash
# Build frontend (if needed), start MinIO, run FastAPI backend only.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f app/main.py ]]; then
  echo "Error: run from the kairo project root." >&2
  exit 1
fi

if [[ ! -f app/static/index.html ]]; then
  echo "Frontend not built — running build_frontend.sh ..."
  bash scripts/build_frontend.sh
else
  echo "Using existing app/static/ build (remove index.html to force rebuild)."
fi

echo "Starting MinIO (docker compose)..."
docker compose up -d minio minio-init

echo ""
echo "MinIO API:     http://127.0.0.1:7000"
echo "MinIO Console: http://127.0.0.1:7001"
echo "Backend:       http://127.0.0.1:8000"
echo "UPLOAD_BACKEND=minio (see .env)"
echo ""

exec python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --proxy-headers
