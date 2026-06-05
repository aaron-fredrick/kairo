import enum
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.orm.base_orm import TimestampMixin

if TYPE_CHECKING:
    from app.infrastructure.db.orm.message_orm import MessageORM


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    NORMAL = "normal"


class UserORM(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=True)
    pfp_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(
        SAEnum(UserRole, values_callable=lambda e: [m.value for m in e]),
        default=UserRole.NORMAL.value,
        nullable=False,
    )

    messages: Mapped[List["MessageORM"]] = relationship(
        back_populates="sender", cascade="all, delete-orphan"
    )
