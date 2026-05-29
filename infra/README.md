# Infrastructure

- **`docker/app.Dockerfile`** — **app-backend** image (API + built frontend static assets).
- **`docker/register.Dockerfile`** — **app-register** image.
- **`proxy/caddy/`** — Static Caddy snippets for compose profiles.
- **`proxy/nginx/`** — Example nginx config when `PROXY_TYPE=nginx`.

Compose stacks live in [`../compose/`](../compose/README.md).
