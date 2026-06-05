from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.orm.user_orm import UserORM
from app.infrastructure.dtos.user_dto import UserDTO
from app.infrastructure.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[UserORM, UserDTO]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserORM, session)

    def _to_dto(self, orm_obj: UserORM) -> UserDTO:
        return UserDTO(
            id=orm_obj.id,
            username=orm_obj.username,
            hashed_password=orm_obj.hashed_password,
            pfp_hash=orm_obj.pfp_hash,
            is_anonymous=orm_obj.is_anonymous,
            is_superadmin=orm_obj.is_superadmin,
            role=orm_obj.role,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    async def get_by_username(self, username: str) -> Optional[UserDTO]:
        stmt = select(self._model).filter(self._model.username == username)
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_dto(orm_obj) if orm_obj else None
