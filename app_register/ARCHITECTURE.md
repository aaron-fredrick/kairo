# app-register service architecture

The **app-register** service (`app_register/`) tracks healthy **app-backend** nodes and publishes reverse-proxy configuration (Caddy or Nginx) so a single edge proxy can load-balance HTTP and WebSocket traffic.

## Layered design

```
┌─────────────────────────────────────────────────────────────┐
│  HTTP API (app_register/api.py)                                 │
│  HMAC auth, request/response models                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Application (app_register/services/coordinator.py)             │
│  RegistrationCoordinator — register / heartbeat / deregister│
│  and proxy sync                                             │
└───────────────┬─────────────────────────────┬─────────────────┘
                │                             │
┌───────────────▼──────────────┐   ┌──────────▼─────────────────┐
│  Ports                        │   │  Ports                      │
│  ServerRegistryPort           │   │  ProxyConfigRenderer        │
│  (app_register/ports/registry)  │   │  ProxyConfigPublisher       │
└───────────────┬──────────────┘   └──────────┬─────────────────┘
                │                             │
┌───────────────▼──────────────┐   ┌──────────▼─────────────────┐
│  Adapters                     │   │  Adapters                   │
│  InMemoryServerRegistry       │   │  CaddyProxyRenderer         │
│                               │   │  NginxProxyRenderer         │
│                               │   │  FileProxyPublisher         │
└───────────────────────────────┘   └────────────────────────────┘
                │
┌───────────────▼──────────────┐
│  Domain (app_register/domain)    │
│  AppServerRecord,            │
│  RegisterServerInput         │
└──────────────────────────────┘
```

| Layer | Responsibility |
|-------|----------------|
| **Domain** | Pure data: server records and registration input. No I/O. |
| **Ports** | Protocols (`ServerRegistryPort`, `ProxyConfigRenderer`, `ProxyConfigPublisher`) defining extension points. |
| **Adapters** | Concrete implementations: in-memory registry, Caddy/Nginx renderers, atomic file write + optional reload. |
| **Services** | `RegistrationCoordinator` orchestrates registry mutations and proxy publication. |
| **API** | FastAPI routes, Pydantic schemas, HMAC verification via `shared/service_auth.py`. |
| **Container** | `app_register/container.py` wires default adapters from `RegisterSettings`. |

## Runtime flow

### Registration

1. App node starts with `REGISTER_ENABLED=true` and calls `POST /api/v1/register` signed with `REGISTER_SYSTEM_KEY`.
2. API validates HMAC, builds `RegisterServerInput`, calls `RegistrationCoordinator.register`.
3. `InMemoryServerRegistry` stores a new `AppServerRecord` (UUID, upstream `host:port`, per-server `heartbeat_secret`).
4. Coordinator calls `FileProxyPublisher.publish` with all healthy servers; renderer produces Caddyfile/Nginx config; file is written atomically; optional `PROXY_RELOAD_COMMAND` runs.

### Heartbeats

1. App sends `POST /api/v1/heartbeat/{server_id}` signed with its issued `heartbeat_secret`.
2. Registry updates `last_heartbeat`; proxy config is republished.

### Stale servers

1. Background task in `app_register/main.py` runs every `HEARTBEAT_INTERVAL_SECONDS`.
2. `list_healthy()` prunes records that exceeded `HEARTBEAT_TIMEOUT_SECONDS` (×2 grace) and are no longer alive.
3. If the healthy count changes, proxy config is republished without those upstreams.

### Deregistration

1. App shutdown sends `DELETE /api/v1/register/{server_id}` with system HMAC.
2. Record is removed and proxy config is updated.

## Security

- **System key** (`REGISTER_SYSTEM_KEY`): shared secret for register, list servers, and deregister. Must match on register service and all app nodes.
- **Heartbeat secret**: random per server, returned only in the register response; used for heartbeat requests only.
- **HMAC**: `X-Kairo-Timestamp` + `X-Kairo-Signature` over `timestamp\nMETHOD\npath\nbody` (see `shared/service_auth.py`). Timestamps must be within 60 seconds.

## Configuration

| Variable | Purpose |
|----------|---------|
| `REGISTER_SYSTEM_KEY` | HMAC secret for admin/register API |
| `PROXY_TYPE` | `caddy` (default) or `nginx` |
| `PROXY_CONFIG_PATH` | Where generated config is written |
| `PROXY_RELOAD_COMMAND` | Optional shell command after write (empty in Docker when proxy watches the file) |
| `PUBLIC_LISTEN` | Listen address in generated config (`:80`) |
| `REGISTER_API_PREFIXES` | Comma-separated paths routed to app upstreams (Caddy only) |
| `HEARTBEAT_INTERVAL_SECONDS` | App heartbeat period (returned at register) |
| `HEARTBEAT_TIMEOUT_SECONDS` | Mark server unhealthy after this idle time |

## Extension points

- **Persistent registry**: implement `ServerRegistryPort` (e.g. Redis or PostgreSQL) and pass it to `RegistrationCoordinator` in `container.build_coordinator`.
- **Remote proxy API**: implement `ProxyConfigPublisher` to push config to a control plane instead of a local file.
- **Custom routing**: implement `ProxyConfigRenderer` or extend `CaddyProxyRenderer` for tenant-specific path rules.

## Related packages

- **`app_backend/clients/register_client.py`**: optional client that registers on app-backend lifespan and runs the heartbeat loop.
- **`compose/app-register.yml`**: app-register + Caddy with a shared `proxy_config` volume.
