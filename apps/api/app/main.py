from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
import sys

from app.core.config import settings
from app.container import AppContainer

from app.infrastructure.db.session import check_db_connection
from app.infrastructure.storage.storage_client import check_storage_connection
from app import observability

from app.api import api_router, register_exception_handlers
from app.health import health_router

logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Running startup connection checks...")

        await check_db_connection()
        await check_storage_connection()

        logger.info("Startup connection checks passed.")

        # ----------------------------
        # Build shared infrastructure
        # ----------------------------
        container = AppContainer()
        app.state.container = container

        logger.info("Application container initialized.")

    except Exception as e:
        logger.critical(
            "Startup checks failed. Exiting.",
            error=str(e),
        )
        raise RuntimeError("Application startup failed due to connection errors.") from e

    try:
        yield
    finally:
        logger.info("Shutting down api app...")
        container = getattr(app.state, "container", None)
        if container:
            await container.close()
        logger.info("Shutdown complete.")

app = FastAPI(
    title="Kairo API",
    version="1.0.0-dev",
    openapi_version="3.1.0",
    description="Kairo Microservice API",
    terms_of_service="http://example.com/terms/",
    contact={
        "name": "API Support",
        "url": "http://www.example.com/support",
        "email": "support@example.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    servers=[
        {
            "url": settings.SERVER_URL,
            "description": "Current Environment"
        }
    ],
    openapi_tags=[
        # TODO: add more tags to supoort for routers
        {
            "name": "Auth",
            "description": "Authentication and authorization endpoints."
        }
    ],
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.middleware("http")(observability.middleware.request_id_middleware)
app.middleware("http")(observability.middleware.metrics_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

observability.setup(app)
register_exception_handlers(app)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", exc_info=exc, path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal Server Error"}
    )

app.include_router(api_router)
app.include_router(health_router)
