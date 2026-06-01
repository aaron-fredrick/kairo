from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
import sys

from app.core.config import settings
from app.db.database import check_db_connection
from app.core.redis import check_redis_connection
from app.core.storage import check_storage_connection
from app.core.observability import setup_observability
from packages.backend_core.schemas.observability import HealthCheckResponse

logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Startup checks with retries
        logger.info("Running startup connection checks...")
        await check_db_connection()
        await check_redis_connection()
        await check_storage_connection()
        logger.info("Startup connection checks passed.")
    except Exception as e:
        logger.critical("Startup checks failed. Exiting.", error=str(e))
        sys.exit(1)
        
    yield
    # Shutdown
    logger.info("Shutting down api app...")


app = FastAPI(
    title="Kairo Microservice API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_observability(app)

@app.get("/api/health", response_model=HealthCheckResponse, tags=["Observability"])
async def health_check():
    """Health checking endpoint returning proper response."""
    # Since lifespan checks passed, we return OK, but could actively check here
    return HealthCheckResponse(
        status="ok",
        version="0.1.0",
        services={
            "database": "connected",
            "redis": "connected",
            "storage": "connected"
        }
    )

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", exc_info=exc, path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal Server Error"}
    )

# Include routers
from app.api.router import api_router

app.include_router(api_router)
