from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db_session
from app.mediators.auth_mediator import AuthMediator
from app.schemas.auth import Token, UserRegister, UserResponse
from app.core.security import get_current_user_id
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])

def get_auth_mediator(session: AsyncSession = Depends(get_db_session)) -> AuthMediator:
    return AuthMediator(session)

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    mediator: AuthMediator = Depends(get_auth_mediator)
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    from app.schemas.auth import UserLogin
    login_data = UserLogin(username=form_data.username, password=form_data.password)
    return await mediator.authenticate_user(login_data)

@router.post("/register", response_model=UserResponse)
async def register(
    register_data: UserRegister,
    mediator: AuthMediator = Depends(get_auth_mediator)
):
    """
    Register a new normal user.
    """
    return await mediator.register_user(register_data)

@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: int = Depends(get_current_user_id),
    mediator: AuthMediator = Depends(get_auth_mediator)
):
    """
    Get current logged in user profile.
    """
    return await mediator.get_current_user_profile(user_id)

@router.post("/join")
async def anonymous_join(
    mediator: AuthMediator = Depends(get_auth_mediator)
):
    """
    Register an anonymous user and immediately return token and user details.
    """
    from app.schemas.auth import UserRegister
    # register_user handles empty username by generating anonymous user
    user = await mediator.register_user(UserRegister())
    # We need the token. However, auth_mediator.register_user doesn't return the raw password.
    # To fix this, we should add an explicit join method to the mediator.
    return await mediator.anonymous_join()
