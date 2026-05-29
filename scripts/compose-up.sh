#!/usr/bin/env bash
# Start a compose profile (short names supported — see scripts/README.md).
#
#   ./scripts/compose-up.sh local
#   ./scripts/compose-up.sh distributed --scale app-backend=2
#   ./scripts/compose-up.sh app-backend.local-dev
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=lib/compose-lib.sh
source "$ROOT/scripts/lib/compose-lib.sh"

PROFILE="${1:?profile required (local, local-dev, standalone, register, workers, distributed, minio, …)}"
shift || true
mapfile -t FILES < <(compose_files_args "$PROFILE")
exec docker compose "${FILES[@]}" up --build "$@"
