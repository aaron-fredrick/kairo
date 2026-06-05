from typing import TYPE_CHECKING, List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.orm.base_orm import TimestampMixin

if TYPE_CHECKING:
    from app.infrastructure.db.orm.message_orm import MessageORM


class RoomORM(Base, TimestampMixin):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=True)

    messages: Mapped[List["MessageORM"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
