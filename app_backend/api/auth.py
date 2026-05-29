from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app_backend.auth.jwt import create_access_token, verify_password
from app_backend.core.logging import get_logger
from app_backend.db.database import get_db
from app_backend.core.state import get_state_manager, StateManager
from app_backend.models.user import User
from app_backend.services.auth_service import auth_service

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class ServerJoinRequest(BaseModel):
    password: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


@router.post("/join", response_model=TokenResponse)
async def join_server(
    request: ServerJoinRequest,
    db: AsyncSession = Depends(get_db),
    state: StateManager = Depends(get_state_manager),
) -> TokenResponse:
    """
    Assign the caller an adjective-noun username and return a signed JWT.

    Optionally validates a server password when the server is password-protected.
    """
    logger.debug("Join request received (password_provided=%s)", request.password is not None)
    username, access_token = await auth_service.join_server(state, db, request.password)
    logger.info("Anonymous client joined as '%s'", username)
    return TokenResponse(access_token=access_token, username=username, role="normal")


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
    state: StateManager = Depends(get_state_manager),
) -> TokenResponse:
    """
    Authenticate a named user (admin or moderator) with username + password.

    Returns a JWT embedding the user's role so the WS layer and API can enforce
    room-level access control without an extra DB round-trip.
    """
    result = await db.execute(select(User).where(User.username == request.username))
    user: User | None = result.scalars().first()

    if not user or user.is_anonymous or not user.hashed_password:
        logger.warning("Login failed: unknown user '%s'", request.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    if not verify_password(request.password, user.hashed_password):
        logger.warning("Login failed: wrong password for user '%s'", request.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    import time
    from app_backend.core.config import settings

    expire_time = int(time.time()) + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    await state.set_user_active(user.username, expire_time)

    access_token = create_access_token(data={"sub": user.username, "role": user.role})

    logger.info("Named user '%s' (role=%s) logged in", user.username, user.role)
    return TokenResponse(
        access_token=access_token,
        username=user.username,
        role=user.role,
    )
