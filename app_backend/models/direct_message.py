from sqlalchemy import Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from app_backend.db.database import Base
from app_backend.models.base import TimestampMixin

if TYPE_CHECKING:
    from app_backend.models.user import User


class DirectMessage(Base, TimestampMixin):
    __tablename__ = "direct_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    sender: Mapped["User"] = relationship(foreign_keys=[sender_id])
    recipient: Mapped["User"] = relationship(foreign_keys=[recipient_id])

    # Composite index for conversation history queries
    __table_args__ = (
        Index("ix_dm_conversation", "sender_id", "recipient_id"),
    )
