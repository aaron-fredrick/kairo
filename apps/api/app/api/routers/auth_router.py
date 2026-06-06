from fastapi import APIRouter, Depends, HTTPException, status
import structlog

from app.api.dependencies.auth import get_current_user_id
from app.api.dependencies.services import get_auth_service
from app.application.services.auth_service import AuthService
from app.schemas.auth_schema import TokenSchema, UserResponseSchema, UserRegisterResponseSchema, RefreshTokenRequestSchema, LoginRequestSchema

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    response_model=UserRegisterResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate a user using their username and password. Returns user profile and token pair.",
    operation_id="user_login",
    responses={
        401: {"description": "Invalid credentials"}
    }
)
async def login(
    request: LoginRequestSchema,
    service: AuthService = Depends(get_auth_service)
):
    logger.debug("Handling login request", username=request.username)
    try:
        user_domain, access_token, refresh_token = await service.login(request.username, request.password)
        return UserRegisterResponseSchema(
            user=UserResponseSchema.model_validate(user_domain),
            token=TokenSchema(access_token=access_token, refresh_token=refresh_token, token_type="bearer")
        )
    except ValueError as e:
        logger.warning("Login failed", error=str(e), username=request.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout User",
    description="Logout the current user, clear their session cache, and emit a logout event if applicable.",
    operation_id="user_logout",
    responses={
        401: {"description": "Not authenticated"}
    }
)
async def logout(
    user_id: int = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service)
):
    logger.debug("Handling logout request", user_id=user_id)
    await service.logout(user_id)
    return {"detail": "Successfully logged out"}


@router.get(
    "/register",
    response_model=UserRegisterResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Anonymous Join",
    description="Create a new temporary anonymous user session with an auto-generated username. Emits a registration event.",
    operation_id="anonymous_join"
)
async def register(service: AuthService = Depends(get_auth_service)):
    logger.debug("Handling anonymous registration request")
    user_domain, access_token, refresh_token = await service.anonymous_join()
    return UserRegisterResponseSchema(
        user=UserResponseSchema.model_validate(user_domain),
        token=TokenSchema(access_token=access_token, refresh_token=refresh_token, token_type="bearer")
    )


@router.post(
    "/refresh",
    response_model=TokenSchema,
    summary="Refresh Session",
    description="Reset the session TTL back to 30 minutes and return a fresh access and refresh token pair.",
    operation_id="refresh_session",
    responses={
        401: {"description": "Invalid or expired refresh token"}
    }
)
async def refresh_token(
    request: RefreshTokenRequestSchema,
    service: AuthService = Depends(get_auth_service)
):
    logger.debug("Handling token refresh request")
    try:
        new_access_token, new_refresh_token = await service.refresh_session(request.refresh_token)
        return TokenSchema(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
    except ValueError as e:
        logger.warning("Token refresh failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get(
    "/me",
    response_model=UserResponseSchema,
    summary="Get Current User",
    description="Return the current user's profile from the session cache.",
    operation_id="get_me",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Session expired or user not found"}
    }
)
async def get_me(
    user_id: int = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service)
):
    logger.debug("Handling get current user request", user_id=user_id)
    try:
        user_domain = await service.get_me(user_id)
        return UserResponseSchema.model_validate(user_domain)
    except ValueError as e:
        logger.warning("Get current user failed", error=str(e), user_id=user_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
