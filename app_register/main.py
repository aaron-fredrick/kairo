"""Kairo register server — app discovery and load-balancer config generation."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app_register.api import router
from app_register.config import settings
from app_register.container import get_coordinator


async def _prune_loop() -> None:
    coordinator = get_coordinator()
    while True:
        await asyncio.sleep(settings.HEARTBEAT_INTERVAL_SECONDS)
        await coordinator.prune_and_sync_if_changed()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    coordinator = get_coordinator()
    prune_task = asyncio.create_task(_prune_loop())
    await coordinator.publish_proxy_config([])
    yield
    prune_task.cancel()
    try:
        await prune_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Kairo Register",
    description="Service registry and dynamic reverse-proxy configuration",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app_register.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENV == "development",
    )
