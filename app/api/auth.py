from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.db.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # TODO: Implement user registration
    return TokenResponse(access_token="placeholder_token_register", username=user_data.username)

@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate and login user."""
    # TODO: Implement login verification
    return TokenResponse(access_token="placeholder_token_login", username=user_data.username)

@router.post("/guest", response_model=TokenResponse)
async def guest_login(db: AsyncSession = Depends(get_db)):
    """Authenticate guest anonymously with adjective-noun username."""
    # TODO: Implement anonymous guest account creation
    return TokenResponse(access_token="placeholder_token_guest", username="anonymous-fox-123")
