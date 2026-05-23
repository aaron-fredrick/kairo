import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from redis.asyncio import Redis

from app.core.config import settings
from app.core.logging import get_logger
from app.db.redis import get_redis

logger = get_logger(__name__)

security = HTTPBearer()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches the stored bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate and return a bcrypt hash for the given password."""
    return _pwd_context.hash(password)


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


async def get_current_username(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis: Redis = Depends(get_redis),
) -> str:
    """
    FastAPI dependency that extracts and validates a Bearer token.

    Validates the JWT signature, checks that the subject is still registered
    in Redis as an active session, and slides the session expiry window forward.

    Raises HTTP 401 on any validation failure.
    """
    # Lazy import avoids the circular dependency between jwt ↔ auth_service
    from app.services.auth_service import auth_service  # noqa: PLC0415

    token = credentials.credentials
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

    current_time = time.time()
    score = await redis.zscore("active_users", username)

    if score is None or score < current_time:
        logger.info("Session expired or unknown for user '%s'", username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired, please join again",
        )

    logger.debug("Authenticated request for user '%s'", username)
    await auth_service.refresh_user_activity(redis, username)
    return username
