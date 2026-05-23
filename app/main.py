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
from app.db.database import engine
from app.db.redis import redis_manager
from app.ws.router import router as ws_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting Kairo server (env=%s, debug=%s)", settings.ENV, settings.DEBUG)

    logger.debug("Connecting to Redis at %s", settings.REDIS_URL)
    redis_manager.connect()
    logger.info("Redis connection established")

    logger.debug("Verifying PostgreSQL connection at %s", settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("PostgreSQL connection pool ready")

    yield

    logger.info("Shutting down Kairo server")
    await redis_manager.disconnect()
    logger.debug("Redis connection closed")

    await engine.dispose()
    logger.debug("PostgreSQL connection pool disposed")


app = FastAPI(
    title="Kairo API",
    description="Realtime chat communication server",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(IPAccessMiddleware)

app.include_router(api_router)
app.include_router(ws_router)

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
