from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.orm.base_orm import TimestampMixin

if TYPE_CHECKING:
    from app.infrastructure.db.orm.attachment_orm import AttachmentORM
    from app.infrastructure.db.orm.room_orm import RoomORM
    from app.infrastructure.db.orm.user_orm import UserORM


class MessageORM(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )

    sender: Mapped["UserORM"] = relationship(back_populates="messages")
    room: Mapped["RoomORM"] = relationship(back_populates="messages")
    attachments: Mapped[List["AttachmentORM"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
