from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import structlog

from app.api.dependencies.auth import get_current_user_id, get_current_user_id_optional
from app.api.dependencies.services import get_auth_service
from app.application.services.auth_service import AuthService
from app.schemas.auth_schema import TokenSchema, UserRegisterSchema, UserResponseSchema, UserLoginSchema, UserJoinResponseSchema

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=TokenSchema)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service)
):
    pass

@router.post("/register", response_model=UserResponseSchema)
async def register(
    register_data: UserRegisterSchema,
    service: AuthService = Depends(get_auth_service)
):
    pass

@router.get("/me", response_model=UserResponseSchema)
async def get_me(
    user_id: int = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service)
):
    pass

@router.post("/join", response_model=UserJoinResponseSchema)
async def anonymous_join(
    user_id: int | None = Depends(get_current_user_id_optional),
    service: AuthService = Depends(get_auth_service)
):
    if user_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already registered and authenticated"
        )
        
    user_domain, token = await service.anonymous_join()
    
    return UserJoinResponseSchema(
        user=UserResponseSchema(
            id=user_domain.id,
            username=user_domain.username,
            is_superadmin=user_domain.is_superadmin,
            role=user_domain.role,
            pfp_hash=user_domain.pfp_hash
        ),
        token=TokenSchema(access_token=token, token_type="bearer")
    )
