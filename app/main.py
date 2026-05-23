from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.middleware import IPAccessMiddleware
from app.api.router import api_router
from app.ws.router import router as ws_router
from app.db.redis import redis_manager
from app.db.database import engine
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence:
    # 1. Initialize Redis connection
    redis_manager.connect()
    # 2. Verify database connection pool
    async with engine.begin() as conn:
        # Simple test query to ensure connection is working
        await conn.execute("SELECT 1")
    
    yield
    
    # Shutdown sequence:
    # 1. Close Redis connection
    await redis_manager.disconnect()
    # 2. Close PostgreSQL connection pool
    await engine.dispose()

app = FastAPI(
    title="Kairo API",
    description="Realtime chat communication server",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# IP Blacklist / Whitelist Middleware
app.add_middleware(IPAccessMiddleware)

# Include API Router and WebSockets Router
app.include_router(api_router)
app.include_router(ws_router)

# Mount frontend static assets if the folder exists, otherwise create a placeholder
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

# Mount static serving
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
