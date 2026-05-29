#!/usr/bin/env bash
# Show containers for a profile.
#   ./scripts/compose-ps.sh local
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=lib/compose-lib.sh
source "$ROOT/scripts/lib/compose-lib.sh"

PROFILE="${1:-local}"
mapfile -t FILES < <(compose_files_args "$PROFILE")
exec docker compose "${FILES[@]}" ps "$@"
