from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.orm.room_orm import RoomORM
from app.infrastructure.dtos.room_dto import RoomDTO
from app.infrastructure.repositories.base_repository import BaseRepository


class RoomRepository(BaseRepository[RoomORM, RoomDTO]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RoomORM, session)

    def _to_dto(self, orm_obj: RoomORM) -> RoomDTO:
        return RoomDTO(
            id=orm_obj.id,
            name=orm_obj.name,
            description=orm_obj.description,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    async def get_by_name(self, name: str) -> Optional[RoomDTO]:
        stmt = select(self._model).filter(self._model.name == name)
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_dto(orm_obj) if orm_obj else None
