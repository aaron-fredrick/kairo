# Shared Docker Compose helpers — source from other scripts.
# Usage: source "$(dirname "$0")/lib/compose-lib.sh"

compose_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd
}

# Map short names to compose profile filenames (without .yml).
compose_resolve_profile() {
  case "${1:-}" in
    local) echo app-backend.local ;;
    local-dev|dev) echo app-backend.local-dev ;;
    standalone) echo app-backend.standalone ;;
    workers) echo app-backend.workers ;;
    register) echo app-register ;;
    distributed|stack) echo stack.distributed ;;
    minio) echo infra.minio ;;
    postgresql|postgres) echo infra.postgresql ;;
    redis) echo infra.redis ;;
    base) echo base ;;
    "") echo app-backend.local ;;
    *) echo "$1" ;;
  esac
}

compose_overlay_path() {
  local profile
  profile="$(compose_resolve_profile "$1")"
  echo "compose/${profile}.yml"
}

compose_files_args() {
  local profile overlay
  profile="$(compose_resolve_profile "$1")"
  overlay="$(compose_overlay_path "$profile")"
  if [[ ! -f "$overlay" ]]; then
    echo "Unknown compose profile: $1 (resolved: $profile)" >&2
    return 1
  fi
  case "$profile" in
    stack.distributed|base|infra.*|app-backend.local|app-backend.local-dev)
      printf '%s\n' -f "$overlay"
      ;;
    *)
      printf '%s\n' -f compose/base.yml -f "$overlay"
      ;;
  esac
}

compose_exec() {
  local profile=$1
  shift
  local -a files
  mapfile -t files < <(compose_files_args "$profile")
  docker compose "${files[@]}" "$@"
}
