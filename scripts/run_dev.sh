#!/usr/bin/env bash
# Native local-dev — hot-reload API (:8000) + Vite (:5173), no Docker.
#
#   ./scripts/run_dev.sh
# Same as compose profile "local-dev", but runs on the host.
set -euo pipefail
# shellcheck source=lib/run-lib.sh
source "$(dirname "$0")/lib/run-lib.sh"
cd "$(run_root)"

run_load_env
run_print_native_banner
run_ensure_frontend_deps

export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:8000}"

echo "API:      http://127.0.0.1:8000  (reload)"
echo "Frontend: http://127.0.0.1:5173  (Vite)"
echo ""

cleanup() {
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

(cd frontend && npm run dev) &
FRONTEND_PID=$!

exec python -m uvicorn app_backend.main:app --host 127.0.0.1 --port 8000 --reload --proxy-headers
