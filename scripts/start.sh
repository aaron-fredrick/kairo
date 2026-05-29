#!/usr/bin/env bash
# Alias for run.sh (native local, no Docker).
exec "$(dirname "$0")/run.sh" "$@"
