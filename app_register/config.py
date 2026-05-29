"""Register service configuration."""
from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class RegisterSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: str = os.getenv("ENV", "production")
    HOST: str = os.getenv("REGISTER_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("REGISTER_PORT", "8100"))

    # Must match app servers' REGISTER_SYSTEM_KEY
    REGISTER_SYSTEM_KEY: str = os.getenv("REGISTER_SYSTEM_KEY", "change_me_register_system_key")

    PROXY_TYPE: str = os.getenv("PROXY_TYPE", "caddy")  # caddy | nginx
    PROXY_CONFIG_PATH: str = os.getenv(
        "PROXY_CONFIG_PATH",
        "/etc/caddy/Caddyfile",
    )
    PROXY_RELOAD_COMMAND: str = os.getenv(
        "PROXY_RELOAD_COMMAND",
        "caddy reload --config /etc/caddy/Caddyfile",
    )
    PUBLIC_LISTEN: str = os.getenv("PUBLIC_LISTEN", ":80")

    HEARTBEAT_INTERVAL_SECONDS: int = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "15"))
    HEARTBEAT_TIMEOUT_SECONDS: int = int(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "45"))

    # Upstream path prefixes forwarded to app servers
    API_PREFIXES: str = os.getenv(
        "REGISTER_API_PREFIXES",
        "/api,/auth,/ws,/docs,/openapi.json",
    )

    @property
    def api_prefixes_list(self) -> list[str]:
        return [p.strip() for p in self.API_PREFIXES.split(",") if p.strip()]


settings = RegisterSettings()
