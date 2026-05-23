from fastapi import APIRouter, Depends
from pydantic import BaseModel
from redis.asyncio import Redis

from app.core.logging import get_logger
from app.db.redis import get_redis
from app.services.auth_service import auth_service

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class ServerJoinRequest(BaseModel):
    password: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


@router.post("/join", response_model=TokenResponse)
async def join_server(
    request: ServerJoinRequest,
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    """
    Assign the caller an adjective-noun username and return a signed JWT.

    Optionally validates a server password when the server is password-protected.
    """
    logger.debug("Join request received (password_provided=%s)", request.password is not None)
    username, access_token = await auth_service.join_server(redis, request.password)
    logger.info("Client joined as '%s'", username)
    return TokenResponse(access_token=access_token, username=username)
