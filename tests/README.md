# Tests

Layout mirrors the main packages:

```
tests/
  src/backend/     # Chat API
    unit/
    component/
    integration/
    smoke/
    e2e/
  src/register/    # Service registry
    unit/
    component/
  shared/          # Cross-service (e.g. HMAC auth)
    unit/
  frontend/        # UI (placeholder for future tests)
    unit/
```

Markers are applied from directory names (`unit`, `component`, …) and package (`src/backend`, `src/register`, …). See `pytest.ini`.

```bash
pytest tests/src/backend tests/src/register tests/shared
pytest tests/src/backend -m integration
pytest tests/src/register -m component
```
