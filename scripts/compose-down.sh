#!/usr/bin/env bash
# Stop a compose profile (same -f files as compose-up).
#
#   ./scripts/compose-down.sh local
#   ./scripts/compose-down.sh distributed -v
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=lib/compose-lib.sh
source "$ROOT/scripts/lib/compose-lib.sh"

PROFILE="${1:-local}"
shift || true
mapfile -t FILES < <(compose_files_args "$PROFILE")
exec docker compose "${FILES[@]}" down "$@"
