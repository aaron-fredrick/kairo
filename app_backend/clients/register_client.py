"""
Register client — app-backend nodes register with app-register when deployed.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from app_backend.core.config import settings
from shared.service_auth import sign_headers

logger = logging.getLogger(__name__)


@dataclass
class RegistrationState:
    server_id: str
    heartbeat_secret: str
    heartbeat_interval_seconds: int


class RegisterClient:
    def __init__(self) -> None:
        self._state: Optional[RegistrationState] = None
        self._task: Optional[asyncio.Task] = None
        self._http: Optional[httpx.AsyncClient] = None

    @property
    def enabled(self) -> bool:
        return bool(settings.REGISTER_ENABLED and settings.REGISTER_URL and settings.REGISTER_SYSTEM_KEY)

    async def start(self) -> None:
        if not self.enabled:
            logger.debug("Register client disabled")
            return
        self._http = httpx.AsyncClient(base_url=settings.REGISTER_URL.rstrip("/"), timeout=30.0)
        await self._register()
        interval = self._state.heartbeat_interval_seconds if self._state else settings.REGISTER_HEARTBEAT_INTERVAL
        self._task = asyncio.create_task(self._heartbeat_loop(interval))

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._state and self._http:
            try:
                path = f"/api/v1/register/{self._state.server_id}"
                headers = sign_headers(settings.REGISTER_SYSTEM_KEY, "DELETE", path, b"")
                await self._http.delete(path, headers=headers)
            except Exception as exc:
                logger.warning("Deregister failed: %s", exc)
        if self._http:
            await self._http.aclose()
            self._http = None
        self._state = None

    async def _register(self) -> None:
        assert self._http is not None
        body = {
            "host": settings.REGISTER_INSTANCE_HOST,
            "port": settings.REGISTER_INSTANCE_PORT,
            "scheme": settings.REGISTER_INSTANCE_SCHEME,
            "hostname": settings.REGISTER_INSTANCE_NAME or settings.REGISTER_INSTANCE_HOST,
            "tags": ["api", "ws"],
        }
        raw = json.dumps(body).encode()
        path = "/api/v1/register"
        headers = sign_headers(settings.REGISTER_SYSTEM_KEY, "POST", path, raw)
        headers["Content-Type"] = "application/json"
        resp = await self._http.post(path, content=raw, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        self._state = RegistrationState(
            server_id=data["server_id"],
            heartbeat_secret=data["heartbeat_secret"],
            heartbeat_interval_seconds=int(data["heartbeat_interval_seconds"]),
        )
        logger.info("Registered with app-register as server_id=%s", self._state.server_id)

    async def _heartbeat_loop(self, interval: int) -> None:
        while True:
            await asyncio.sleep(interval)
            try:
                await self._send_heartbeat()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Heartbeat failed: %s", exc)

    async def _send_heartbeat(self) -> None:
        if not self._http or not self._state:
            return
        path = f"/api/v1/heartbeat/{self._state.server_id}"
        headers = sign_headers(self._state.heartbeat_secret, "POST", path, b"")
        resp = await self._http.post(path, content=b"", headers=headers)
        resp.raise_for_status()


register_client = RegisterClient()
