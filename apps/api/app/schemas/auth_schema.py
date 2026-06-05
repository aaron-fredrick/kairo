from pydantic import BaseModel
from typing import Optional

class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class RefreshTokenRequestSchema(BaseModel):
    refresh_token: str

class UserLoginSchema(BaseModel):
    username: str
    password: str

class UserRegisterSchema(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None

class UserResponseSchema(BaseModel):
    id: int
    username: str
    is_superadmin: bool
    role: str
    pfp_hash: Optional[str] = None

    class Config:
        from_attributes = True

class UserJoinResponseSchema(BaseModel):
    user: UserResponseSchema
    token: TokenSchema