from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_username
from app.db.database import get_db
from app.models.user import User, UserRole


async def get_current_user(
    username: str = Depends(get_current_username),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated username to a full User ORM instance."""
    result = await db.execute(select(User).where(User.username == username))
    user: Optional[User] = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user not found in database.",
        )

    return user


def require_role(*allowed_roles: UserRole):
    """
    Return a FastAPI dependency that raises HTTP 403 if the current user's
    role is not in the supplied set of allowed roles.
    """
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in [r.value for r in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return dependency


require_admin = require_role(UserRole.ADMIN)
require_admin_or_moderator = require_role(UserRole.ADMIN, UserRole.MODERATOR)
