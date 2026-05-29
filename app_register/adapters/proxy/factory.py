"""Factory helpers for proxy adapters."""
from __future__ import annotations

from app_register.adapters.proxy.caddy import CaddyProxyRenderer
from app_register.adapters.proxy.file_publisher import FileProxyPublisher
from app_register.adapters.proxy.nginx import NginxProxyRenderer
from app_register.config import RegisterSettings
from app_register.ports.proxy import ProxyConfigPublisher, ProxyConfigRenderer


def build_proxy_renderer(settings: RegisterSettings) -> ProxyConfigRenderer:
    if settings.PROXY_TYPE.lower() == "nginx":
        return NginxProxyRenderer(public_listen=settings.PUBLIC_LISTEN)
    return CaddyProxyRenderer(
        public_listen=settings.PUBLIC_LISTEN,
        api_prefixes=settings.api_prefixes_list,
    )


def build_proxy_publisher(settings: RegisterSettings) -> ProxyConfigPublisher:
    renderer = build_proxy_renderer(settings)
    return FileProxyPublisher(
        renderer,
        config_path=settings.PROXY_CONFIG_PATH,
        reload_command=settings.PROXY_RELOAD_COMMAND,
    )
