import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import bcrypt as _bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from redis.asyncio import Redis

from app.core.config import settings
from app.core.logging import get_logger
from app.core.state import get_state_manager, StateManager

logger = get_logger(__name__)

security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches the stored bcrypt hash."""
    return _bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """Generate and return a bcrypt hash for the given password."""
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Build and sign a JWT access token from the supplied claims dict.

    The 'exp' claim is automatically added based on expires_delta or the
    global ACCESS_TOKEN_EXPIRE_MINUTES setting.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire

    token = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    logger.debug("Access token created for subject '%s'", data.get("sub", "<unknown>"))
    return token


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT access token.

    Returns the claims dict on success, or None if the token is invalid or
    expired.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as exc:
        logger.debug("JWT decode failed: %s", exc)
        return None


async def get_current_user_payload(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    state: StateManager = Depends(get_state_manager),
) -> Dict[str, Any]:
    """
    FastAPI dependency that extracts and validates a Bearer token, returning the full payload.
    Supports both Authorization header and 'token' query parameter.
    """
    from app.services.auth_service import auth_service  # noqa: PLC0415

    token = None
    if credentials:
        token = credentials.credentials
    elif "token" in request.query_params:
        token = request.query_params["token"]
    elif "kairo_token" in request.cookies:
        token = request.cookies["kairo_token"]

    if not token:
        logger.warning("Request rejected: missing JWT token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)

    if not payload:
        logger.warning("Request rejected: invalid or malformed JWT token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: Optional[str] = payload.get("sub")
    if username is None:
        logger.warning("Request rejected: JWT token is missing 'sub' claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    is_active = await state.is_user_active(username)

    if not is_active:
        logger.info("Session expired or unknown for user '%s'", username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired, please join again",
        )

    logger.debug("Authenticated request for user '%s'", username)
    await auth_service.refresh_user_activity(state, username)
    return payload


async def get_current_username(
    payload: Dict[str, Any] = Depends(get_current_user_payload),
) -> str:
    """
    FastAPI dependency that returns the username of the authenticated user.
    """
    return payload["sub"]
