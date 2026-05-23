from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from redis.asyncio import Redis
from app.db.redis import get_redis
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

class ServerJoinRequest(BaseModel):
    password: str = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str

@router.post("/join", response_model=TokenResponse)
async def join_server(
    request: ServerJoinRequest, 
    redis: Redis = Depends(get_redis)
):
    """Join the server, receiving an adjective-noun username and token."""
    username, access_token = await auth_service.join_server(redis, request.password)
    return TokenResponse(
        access_token=access_token, 
        username=username
    )
