#!/usr/bin/env bash
# Quick project sanity check (no full CI suite).
#
#   ./scripts/check.sh           # fast: smoke + shared + app_register unit
#   ./scripts/check.sh --full      # + app_backend unit/component
#   ./scripts/check.sh --http      # also curl edge if stack is on :80
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FULL=false
HTTP=false
for arg in "$@"; do
  case "$arg" in
    --full) FULL=true ;;
    --http) HTTP=true ;;
    -h|--help)
      echo "Usage: $0 [--full] [--http]"
      exit 0
      ;;
  esac
done

echo "==> Python import check"
python -c "import app_backend.main; import app_register.main; print('ok: app_backend, app_register')"

echo ""
echo "==> Pytest (quick)"
PYTEST_ARGS=(tests/app_backend/smoke tests/shared/unit tests/app_register/unit -q --tb=line)
if [[ "$FULL" == true ]]; then
  PYTEST_ARGS=(tests/app_backend tests/app_register tests/shared -m "unit or component or smoke" -q --tb=line)
fi
python -m pytest "${PYTEST_ARGS[@]}"

if [[ "$HTTP" == true ]]; then
  echo ""
  echo "==> HTTP (Caddy :80, if running)"
  if curl -sf --max-time 3 http://127.0.0.1/openapi.json >/dev/null 2>&1; then
    echo "ok: http://127.0.0.1/openapi.json"
    curl -sf --max-time 3 -o /dev/null -w "guest join: HTTP %{http_code}\n" \
      -X POST http://127.0.0.1/auth/join -H "Content-Type: application/json" -d "{}"
  else
    echo "skip: nothing on http://127.0.0.1 (start stack: ./scripts/compose-up.sh local)"
  fi
fi

echo ""
echo "==> Done"
