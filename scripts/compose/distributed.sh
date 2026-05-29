#!/usr/bin/env bash
# Full stack: ./scripts/compose/distributed.sh --scale app-backend=2
exec "$(dirname "$0")/../compose-up.sh" distributed "$@"
