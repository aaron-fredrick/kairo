#!/usr/bin/env bash
exec "$(dirname "$0")/../compose-up.sh" local-dev "$@"
