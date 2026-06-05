from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import structlog

from app.api.dependencies.auth import get_current_user_id, get_current_user_id_optional
from app.api.dependencies.services import get_auth_service
from app.application.services.auth_service import AuthService
from app.schemas.auth_schema import TokenSchema, UserRegisterSchema, UserResponseSchema, UserLoginSchema, UserJoinResponseSchema, RefreshTokenRequestSchema

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/refresh", response_model=TokenSchema)
async def refresh_token(
    request: RefreshTokenRequestSchema,
    service: AuthService = Depends(get_auth_service)
):
    try:
        new_access_token, new_refresh_token = await service.refresh_session(request.refresh_token)
        return TokenSchema(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
    except ValueError as e:
        logger.warning("Failed to refresh token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.post("/register", response_model=UserJoinResponseSchema, status_code=status.HTTP_201_CREATED)
async def register(
    register_data: UserRegisterSchema,
    service: AuthService = Depends(get_auth_service)
):
    if not register_data.username or not register_data.password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username and password are required"
        )
    try:
        user_domain, access_token, refresh_token = await service.register(
            register_data.username,
            register_data.password
        )
        return UserJoinResponseSchema(
            user=UserResponseSchema(
                id=user_domain.id,
                username=user_domain.username,
                is_superadmin=user_domain.is_superadmin,
                role=user_domain.role,
                pfp_hash=user_domain.pfp_hash
            ),
            token=TokenSchema(access_token=access_token, refresh_token=refresh_token, token_type="bearer")
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.post("/login", response_model=TokenSchema)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service)
):
    try:
        _, access_token, refresh_token = await service.login(form_data.username, form_data.password)
        return TokenSchema(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )

@router.get("/me", response_model=UserResponseSchema)
async def get_me(
    user_id: int = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service)
):
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

@router.post("/join", response_model=UserJoinResponseSchema)
async def anonymous_join(
    user_id: int | None = Depends(get_current_user_id_optional),
    service: AuthService = Depends(get_auth_service)
):
    logger.debug("Received anonymous join request", existing_user_id=user_id)
    if user_id is not None:
        logger.debug("Rejecting join request: user already authenticated", user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already registered and authenticated"
        )
        
    user_domain, access_token, refresh_token = await service.anonymous_join()
    
    return UserJoinResponseSchema(
        user=UserResponseSchema(
            id=user_domain.id,
            username=user_domain.username,
            is_superadmin=user_domain.is_superadmin,
            role=user_domain.role,
            pfp_hash=user_domain.pfp_hash
        ),
        token=TokenSchema(access_token=access_token, refresh_token=refresh_token, token_type="bearer")
    )
