import enum

from sqlalchemy import String, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING
from app.db.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.message import Message


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    NORMAL = "normal"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(
        SAEnum(UserRole, values_callable=lambda e: [m.value for m in e]),
        default=UserRole.NORMAL.value,
        nullable=False,
    )

    # Relationships
    messages: Mapped[List["Message"]] = relationship(back_populates="sender", cascade="all, delete-orphan")
