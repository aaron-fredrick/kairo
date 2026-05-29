"""Register HTTP API."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app_register.config import settings
from app_register.container import get_coordinator
from app_register.domain.models import RegisterServerInput
from shared.service_auth import verify_headers

router = APIRouter(prefix="/api/v1", tags=["register"])


class RegisterRequest(BaseModel):
    host: str = Field(..., description="Hostname or Docker service name reachable by the proxy")
    port: int = Field(..., ge=1, le=65535)
    scheme: str = Field(default="http")
    hostname: str = Field(default="", description="Human-readable label")
    tags: list[str] = Field(default_factory=lambda: ["api", "ws"])


class RegisterResponse(BaseModel):
    server_id: str
    heartbeat_interval_seconds: int
    heartbeat_secret: str


class HeartbeatResponse(BaseModel):
    server_id: str
    status: str = "ok"


def _require_system_auth(request: Request, body: bytes) -> None:
    if not verify_headers(
        settings.REGISTER_SYSTEM_KEY,
        request.method,
        request.url.path,
        body,
        request.headers,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid register credentials")


def _require_heartbeat_auth(server_id: str, request: Request, body: bytes) -> None:
    coordinator = get_coordinator()
    record = coordinator.get(server_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown server_id")
    if not verify_headers(
        record.heartbeat_secret,
        request.method,
        request.url.path,
        body,
        request.headers,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid heartbeat credentials")


@router.post("/register", response_model=RegisterResponse)
async def register_server(request: Request) -> RegisterResponse:
    body = await request.body()
    _require_system_auth(request, body)
    payload = RegisterRequest.model_validate(json.loads(body or b"{}"))
    coordinator = get_coordinator()
    record = await coordinator.register(
        RegisterServerInput(
            host=payload.host,
            port=payload.port,
            scheme=payload.scheme,
            hostname=payload.hostname,
            tags=tuple(payload.tags),
        )
    )
    return RegisterResponse(
        server_id=record.server_id,
        heartbeat_interval_seconds=coordinator.heartbeat_interval_seconds,
        heartbeat_secret=record.heartbeat_secret,
    )


@router.post("/heartbeat/{server_id}", response_model=HeartbeatResponse)
async def heartbeat(server_id: str, request: Request) -> HeartbeatResponse:
    body = await request.body()
    _require_heartbeat_auth(server_id, request, body)
    coordinator = get_coordinator()
    record = await coordinator.heartbeat(server_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown server_id")
    return HeartbeatResponse(server_id=server_id)


@router.delete("/register/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deregister_server(server_id: str, request: Request) -> None:
    body = await request.body()
    _require_system_auth(request, body)
    coordinator = get_coordinator()
    if not await coordinator.deregister(server_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown server_id")


@router.get("/servers")
async def list_servers(request: Request) -> dict:
    body = await request.body()
    _require_system_auth(request, body)
    healthy = get_coordinator().list_healthy()
    return {
        "healthy": [
            {
                "server_id": s.server_id,
                "upstream": s.upstream,
                "hostname": s.hostname,
                "tags": s.tags,
                "last_heartbeat": s.last_heartbeat,
            }
            for s in healthy
        ]
    }


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "healthy_servers": len(get_coordinator().list_healthy())}
