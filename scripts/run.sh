#!/usr/bin/env bash
# Native local — built frontend served by the API on :8000 (no Docker).
#
#   ./scripts/run.sh
# Same as compose profile "local", but runs on the host.
set -euo pipefail
# shellcheck source=lib/run-lib.sh
source "$(dirname "$0")/lib/run-lib.sh"
cd "$(run_root)"

run_load_env
run_print_native_banner
run_ensure_frontend_built

echo "Open http://127.0.0.1:8000"
echo ""

exec python -m uvicorn app_backend.main:app --host 127.0.0.1 --port 8000 --proxy-headers
