# Shared helpers for native run scripts (no Docker).

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

run_ensure_frontend_built() {
  if [[ ! -f app_backend/static/index.html ]]; then
    echo "Frontend not built — running build_frontend.sh ..."
    bash scripts/build_frontend.sh
  fi
}

run_print_native_banner() {
  echo ""
  echo "Native mode (no Docker). Using .env — defaults: DB_BACKEND=sqlite, EVENT_BUS=local."
  echo "For MinIO/Postgres/Redis, run infra stacks under scripts/compose/ or use Docker: scripts/compose/local.sh"
  echo ""
}
