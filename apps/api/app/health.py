from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict

class HealthCheckResponse(BaseModel):
    status: str
    version: str
    services: Dict[str, str]

health_router = APIRouter(prefix="/health", tags=["Health"])

@health_router.get("", response_model=HealthCheckResponse)
async def health_check():
    """Health checking endpoint returning proper response."""
    return HealthCheckResponse(
        status="ok",
        version="0.1.0",
        services={
            "database": "connected",
            "redis": "connected",
            "storage": "connected"
        }
    )