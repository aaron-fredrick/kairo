from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
import structlog

from app.api.dependencies.auth import get_current_user_id
from app.schemas.auth_schema import TokenSchema, UserRegisterSchema, UserResponseSchema, UserLoginSchema

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])

# Stub service
def get_auth_service():
    pass

@router.post("/login", response_model=TokenSchema)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service = Depends(get_auth_service)
):
    pass

@router.post("/register", response_model=UserResponseSchema)
async def register(
    register_data: UserRegisterSchema,
    service = Depends(get_auth_service)
):
    pass

@router.get("/me", response_model=UserResponseSchema)
async def get_me(
    user_id: int = Depends(get_current_user_id),
    service = Depends(get_auth_service)
):
    pass

@router.post("/join")
async def anonymous_join(
    service = Depends(get_auth_service)
):
    pass
