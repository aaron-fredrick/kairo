#!/usr/bin/env bash
# Shared helpers for native run scripts (no Docker).
# Usage: source "$(dirname "$0")/lib/run-lib.sh"

run_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd
}

run_load_env() {
  if [[ -f .env ]]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
  fi
}

run_ensure_frontend_deps() {
  if [[ ! -d frontend/node_modules ]]; then
    echo "Installing frontend dependencies..."
    (cd frontend && npm install --legacy-peer-deps)
  fi
}

run_build_frontend() {
  if [[ ! -f app_backend/static/index.html ]]; then
    echo "Building frontend into app_backend/static/ ..."
    (cd frontend && npm install --legacy-peer-deps && npm run build)
  fi
}

run_print_native_banner() {
  echo ""
  echo "Native mode (no Docker). Using .env — defaults: DB_BACKEND=sqlite, EVENT_BUS=local."
  echo "For a full containerised stack use: scripts/compose/local.sh"
  echo ""
}
