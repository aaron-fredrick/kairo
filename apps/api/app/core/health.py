from fastapi import APIRouter
from packages.backend_core.schemas.observability import HealthCheckResponse

from src.backend.api import router

health_router = APIRouter(prefix="/health", tags=["Health"])

@router.get(response_model=HealthCheckResponse)
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