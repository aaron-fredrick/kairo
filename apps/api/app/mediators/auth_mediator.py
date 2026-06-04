import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.repositories.user import UserRepository
from app.schemas.auth import UserLogin, UserRegister, Token, UserResponse
from app.core.security import verify_password, get_password_hash, create_access_token

logger = structlog.get_logger(__name__)

class AuthMediator:
    def __init__(self, session: AsyncSession):
        self.user_repo = UserRepository(session)

    async def authenticate_user(self, login_data: UserLogin) -> Token:
        user = await self.user_repo.get_by_username(login_data.username)
        if not user or not user.hashed_password:
            logger.warning("Failed login attempt", username=login_data.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not verify_password(login_data.password, user.hashed_password):
            logger.warning("Failed login attempt", username=login_data.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = create_access_token(subject=user.id)
        logger.info("User authenticated successfully", user_id=user.id)
        return Token(access_token=access_token, token_type="bearer")

    async def register_user(self, register_data: UserRegister) -> UserResponse:
        from app.utils.username import generate_username
        import secrets

        # Auto-generate if not provided
        target_username = register_data.username
        is_anonymous = False
        
        if not target_username:
            target_username = generate_username()
            is_anonymous = True
            
        target_password = register_data.password
        if not target_password:
            target_password = secrets.token_urlsafe(16)

        existing_user = await self.user_repo.get_by_username(target_username)
        if existing_user:
            # If auto-generated hit a collision, we could retry, but throwing 400 is safer for now
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered (collision)"
            )

        hashed_password = get_password_hash(target_password)
        user_in = {
            "username": target_username,
            "hashed_password": hashed_password,
            "is_anonymous": is_anonymous,
            "is_superadmin": False,
            "role": "normal"
        }
        
        new_user = await self.user_repo.create(user_in)
        logger.info("New user registered", user_id=new_user.id)
        return UserResponse.model_validate(new_user)

    async def get_current_user_profile(self, user_id: int) -> UserResponse:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse.model_validate(user)
