#!/usr/bin/env bash
# Tail logs for a profile.
#   ./scripts/compose-logs.sh local
#   ./scripts/compose-logs.sh local-dev app-backend -f
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=lib/compose-lib.sh
source "$ROOT/scripts/lib/compose-lib.sh"

PROFILE="${1:-local}"
shift || true
mapfile -t FILES < <(compose_files_args "$PROFILE")
exec docker compose "${FILES[@]}" logs "$@"
