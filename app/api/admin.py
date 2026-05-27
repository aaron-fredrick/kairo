from typing import Optional

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin, require_admin_or_moderator
from app.core.logging import get_logger
from app.db.database import get_db
from app.models.user import User, UserRole
from app.services.admin_service import admin_service

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateUserRequest(BaseModel):
    role: UserRole
    password: Optional[str] = None


class CreatedUserResponse(BaseModel):
    id: int
    username: str
    role: str
    generated_password: Optional[str] = None

    class Config:
        from_attributes = True


@router.post(
    "/users",
    response_model=CreatedUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an admin or moderator user",
)
async def create_privileged_user(
    request: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> CreatedUserResponse:
    """
    Create a new admin or moderator user.

    - **role**: must be `admin` or `moderator`.
    - **password**: optional. If omitted, a secure random password is generated
      and returned *once* in `generated_password`. Store it immediately — it is
      never shown again.

    Only existing admins may call this endpoint.
    Sub-admins can only create moderators. Only the main superadmin can create admins.
    """
    if request.role == UserRole.ADMIN and not _.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the superadmin can create other admins.",
        )

    was_random = request.password is None
    user, plain_password = await admin_service.create_named_user(
        db=db,
        role=request.role,
        plain_password=request.password,
    )
    logger.info(
        "Admin '%s' created user '%s' (role=%s, password_generated=%s)",
        _.username,
        user.username,
        user.role,
        was_random,
    )
    return CreatedUserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        generated_password=plain_password if was_random else None,
    )


class ManagedUserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_anonymous: bool

    class Config:
        from_attributes = True


@router.get(
    "/users",
    response_model=list[ManagedUserResponse],
    summary="List all named users",
)
async def list_named_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin_or_moderator),
) -> list[ManagedUserResponse]:
    """
    Return all non-anonymous users. Accessible by admins and moderators.
    """
    from sqlalchemy import select
    from app.models.user import User as UserModel
    result = await db.execute(
        select(UserModel).where(UserModel.is_anonymous == False)
    )
    users = result.scalars().all()
    return [
        ManagedUserResponse(
            id=u.id,
            username=u.username,
            role=u.role,
            is_anonymous=u.is_anonymous,
        )
        for u in users
    ]
