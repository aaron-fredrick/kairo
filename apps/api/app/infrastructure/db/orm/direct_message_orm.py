from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.orm.base_orm import TimestampMixin

if TYPE_CHECKING:
    from app.infrastructure.db.orm.user_orm import UserORM


class DirectMessageORM(Base, TimestampMixin):
    __tablename__ = "direct_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    sender: Mapped["UserORM"] = relationship(foreign_keys=[sender_id])
    recipient: Mapped["UserORM"] = relationship(foreign_keys=[recipient_id])

    __table_args__ = (
        Index("ix_dm_conversation", "sender_id", "recipient_id"),
    )
