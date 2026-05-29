#!/usr/bin/env bash
# Scale workers: ./scripts/compose/standalone.sh --scale app-backend=2
exec "$(dirname "$0")/../compose-up.sh" standalone "$@"
