from pydantic import BaseModel, Field
from typing import Optional

class TokenSchema(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(..., description="Type of token, typically 'bearer'", examples=["bearer"])

class RefreshTokenRequestSchema(BaseModel):
    refresh_token: str = Field(..., description="Valid refresh token to obtain a new session")

class LoginRequestSchema(BaseModel):
    username: str = Field(..., description="Username for authentication")
    password: str = Field(..., description="Password for authentication")

class UserResponseSchema(BaseModel):
    id: int = Field(..., description="Unique identifier for the user")
    username: str = Field(..., description="Username of the user")
    is_superadmin: bool = Field(..., description="Whether the user has superadmin privileges")
    role: str = Field(..., description="Role of the user, e.g., 'normal'")
    pfp_hash: Optional[str] = Field(None, description="Hash of the user's profile picture, if any")

    class Config:
        from_attributes = True

class UserRegisterResponseSchema(BaseModel):
    user: UserResponseSchema = Field(..., description="User profile details")
    token: TokenSchema = Field(..., description="Authentication tokens")