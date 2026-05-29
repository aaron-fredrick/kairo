"""Caddy and Nginx proxy renderer tests."""
from __future__ import annotations

from app_register.adapters.proxy.caddy import CaddyProxyRenderer
from app_register.adapters.proxy.nginx import NginxProxyRenderer
from app_register.domain.models import AppServerRecord


def _record(upstream: str = "app:8000") -> AppServerRecord:
    return AppServerRecord(
        server_id="id",
        upstream=upstream,
        scheme="http",
        hostname="app",
        tags=["api"],
        heartbeat_secret="secret",
    )


def test_caddy_empty_upstream() -> None:
    text = CaddyProxyRenderer(public_listen=":80", api_prefixes=["/api"]).render([])
    assert "no app servers registered" in text
    assert ":80" in text


def test_caddy_with_upstream() -> None:
    text = CaddyProxyRenderer(
        public_listen=":8080",
        api_prefixes=["/api", "/ws"],
    ).render([_record(), _record("app2:8000")])
    assert "reverse_proxy app:8000 app2:8000" in text
    assert "handle /api/*" in text
    assert "handle /ws/*" in text
    assert ":8080" in text


def test_nginx_empty_upstream() -> None:
    text = NginxProxyRenderer(public_listen=":80").render([])
    assert "503" in text
    assert "listen 80" in text


def test_nginx_with_upstream() -> None:
    text = NginxProxyRenderer(public_listen=":443").render([_record()])
    assert "upstream kairo_app" in text
    assert "server app:8000;" in text
    assert "proxy_pass http://kairo_app" in text
