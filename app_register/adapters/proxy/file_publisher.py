"""Write proxy config to disk and optionally run a reload command."""
from __future__ import annotations

import asyncio
import logging
import os
import shlex

from app_register.domain.models import AppServerRecord
from app_register.ports.proxy import ProxyConfigPublisher, ProxyConfigRenderer

logger = logging.getLogger(__name__)


class FileProxyPublisher(ProxyConfigPublisher):
    def __init__(
        self,
        renderer: ProxyConfigRenderer,
        *,
        config_path: str,
        reload_command: str = "",
    ) -> None:
        self._renderer = renderer
        self._config_path = config_path
        self._reload_command = reload_command.strip()

    async def publish(self, servers: list[AppServerRecord]) -> None:
        config_text = self._renderer.render(servers)
        path = self._config_path
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            fh.write(config_text)
        os.replace(tmp_path, path)
        logger.info("Wrote proxy config (%d upstreams) to %s", len(servers), path)

        if not self._reload_command:
            return
        parts = shlex.split(self._reload_command)
        loop = asyncio.get_event_loop()

        def _run() -> None:
            import subprocess

            result = subprocess.run(parts, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                logger.error(
                    "Proxy reload failed (%s): %s",
                    self._reload_command,
                    result.stderr or result.stdout,
                )
            else:
                logger.info("Proxy reloaded via: %s", self._reload_command)

        await loop.run_in_executor(None, _run)
