from uuid import UUID
from pydantic import EmailStr
from .common import APIBaseSchema, TimestampMixin


class UserBase(APIBaseSchema):
    username: str
    email: EmailStr


class UserResponse(UserBase, TimestampMixin):
    id: UUID


class UserUpdate(APIBaseSchema):
    username: str | None = None
    email: EmailStr | None = None