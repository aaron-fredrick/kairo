import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import get_logger
from app.core.middleware import IPAccessMiddleware
from app.db.database import engine, AsyncSessionLocal
from app.db.redis import redis_manager
from app.services.admin_service import admin_service
from app.storage.backends import storage_backend
from app.workers.thumbnail import run_thumbnail_worker
from app.workers.broadcast import run_broadcast_worker
from app.ws.router import router as ws_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting Kairo server (env=%s, debug=%s)", settings.ENV, settings.DEBUG)

    if settings.USE_REDIS:
        logger.debug("Connecting to Redis at %s", settings.REDIS_URL)
    else:
        logger.debug("Using mock in-memory Redis")
    redis_manager.connect()
    logger.info("Redis connection established")

    if settings.DB_BACKEND == "sqlite":
        logger.debug("Verifying SQLite connection at %s", settings.SQLITE_URL)
        from app.db.database import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(text("SELECT 1"))
        logger.info("SQLite connection ready")
    else:
        logger.debug("Verifying PostgreSQL connection at %s", settings.DATABASE_URL)
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("PostgreSQL connection pool ready")

    async with AsyncSessionLocal() as seed_session:
        await admin_service.seed_default_admin(seed_session)
        await admin_service.seed_system_rooms(seed_session)
    logger.info("Database seed complete")

    worker_task = asyncio.create_task(run_thumbnail_worker(storage_backend))
    logger.info("Thumbnail worker spawned")
    
    broadcast_task = asyncio.create_task(run_broadcast_worker())
    logger.info("Broadcast worker spawned")

    yield

    logger.info("Shutting down Kairo server")

    worker_task.cancel()
    broadcast_task.cancel()
    try:
        await asyncio.gather(worker_task, broadcast_task, return_exceptions=True)
    except asyncio.CancelledError:
        pass
    logger.debug("Background workers stopped")

    from app.core.event_bus import event_bus
    await event_bus.close()
    logger.debug("Event bus closed")

    await redis_manager.disconnect()
    logger.debug("Redis connection closed")

    await engine.dispose()
    logger.debug("Database connection pool disposed")


app = FastAPI(
    title="Kairo API",
    description="Realtime chat communication server",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(IPAccessMiddleware)

app.include_router(api_router)
app.include_router(ws_router)

# Data directory setup
data_dir = os.path.abspath(settings.DATA_DIR)
os.makedirs(os.path.join(data_dir, "blobs"), exist_ok=True)
os.makedirs(os.path.join(data_dir, "thumbnails"), exist_ok=True)
os.makedirs(os.path.join(data_dir, "db"), exist_ok=True)

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, proxy_headers=True)
