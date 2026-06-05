from fastapi import APIRouter, Depends, HTTPException, status
import structlog

from app.api.dependencies.auth import get_current_user_id
from app.api.dependencies.services import get_auth_service
from app.application.services.auth_service import AuthService
from app.schemas.auth_schema import TokenSchema, UserResponseSchema, UserRegisterResponseSchema, RefreshTokenRequestSchema

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/register", response_model=UserRegisterResponseSchema, status_code=status.HTTP_201_CREATED)
async def register(service: AuthService = Depends(get_auth_service)):
    """Create a new temporary user session with an auto-generated username."""
    user_domain, access_token, refresh_token = await service.anonymous_join()
    return UserRegisterResponseSchema(
        user=UserResponseSchema(
            id=user_domain.id,
            username=user_domain.username,
            is_superadmin=user_domain.is_superadmin,
            role=user_domain.role,
            pfp_hash=user_domain.pfp_hash
        ),
        token=TokenSchema(access_token=access_token, refresh_token=refresh_token, token_type="bearer")
    )


@router.post("/refresh", response_model=TokenSchema)
async def refresh_token(
    request: RefreshTokenRequestSchema,
    service: AuthService = Depends(get_auth_service)
):
    """Reset the session TTL back to 30 minutes and return a fresh token pair."""
    try:
        new_access_token, new_refresh_token = await service.refresh_session(request.refresh_token)
        return TokenSchema(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
    except ValueError as e:
        logger.warning("Failed to refresh token", error=str(e))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me", response_model=UserResponseSchema)
async def get_me(
    user_id: int = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service)
):
    """Return the current user's profile from cache."""
    try:
        user_domain = await service.get_me(user_id)
        return UserResponseSchema(
            id=user_domain.id,
            username=user_domain.username,
            is_superadmin=user_domain.is_superadmin,
            role=user_domain.role,
            pfp_hash=user_domain.pfp_hash
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
