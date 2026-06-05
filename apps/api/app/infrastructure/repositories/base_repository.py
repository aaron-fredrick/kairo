from abc import abstractmethod
from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.base import Base

ORM = TypeVar("ORM", bound=Base)
DTO = TypeVar("DTO")


class BaseRepository(Generic[ORM, DTO]):
    """
    Generic async repository.
    Subclasses must implement _to_dto() to enforce the ORM → DTO boundary.
    All public methods return DTO objects — ORM objects never escape this layer.
    """

    def __init__(self, model: Type[ORM], session: AsyncSession) -> None:
        self._model = model
        self._session = session

    @abstractmethod
    def _to_dto(self, orm_obj: ORM) -> DTO:
        """Map an ORM instance to its corresponding DTO."""

    async def get_by_id(self, id: Any) -> Optional[DTO]:
        stmt = select(self._model).filter(self._model.id == id)
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_dto(orm_obj) if orm_obj else None

    async def get_all(self) -> List[DTO]:
        stmt = select(self._model)
        result = await self._session.execute(stmt)
        return [self._to_dto(obj) for obj in result.scalars().all()]

    async def create(self, data: dict) -> DTO:
        orm_obj = self._model(**data)
        self._session.add(orm_obj)
        await self._session.commit()
        await self._session.refresh(orm_obj)
        return self._to_dto(orm_obj)

    async def update(self, id: Any, data: dict) -> Optional[DTO]:
        stmt = (
            update(self._model)
            .where(self._model.id == id)
            .values(**data)
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        if result.rowcount > 0:
            return await self.get_by_id(id)
        return None

    async def delete(self, id: Any) -> bool:
        stmt = delete(self._model).where(self._model.id == id)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount > 0
