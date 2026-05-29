# Tests

Layout mirrors the main packages:

```
tests/
  app_backend/     # Chat API
    unit/
    component/
    integration/
    smoke/
    e2e/
  app_register/    # Service registry
    unit/
    component/
  shared/          # Cross-service (e.g. HMAC auth)
    unit/
  frontend/        # UI (placeholder for future tests)
    unit/
```

Markers are applied from directory names (`unit`, `component`, …) and package (`app_backend`, `app_register`, …). See `pytest.ini`.

```bash
pytest tests/app_backend tests/app_register tests/shared
pytest tests/app_backend -m integration
pytest tests/app_register -m component
```
