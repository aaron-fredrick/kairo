from sqlalchemy import Column, BigInteger, String, Enum, CheckConstraint, text
from database.models.base import Base
from database.models.enums import AuthType, UserType


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)

    user_type = Column(
        Enum(UserType),
        nullable=False,
        server_default="anonymous"
    )

    auth_type = Column(
        Enum(AuthType),
        nullable=False,
        server_default="anonymous"
    )

    password_hash = Column(String, nullable=True)

    created_at = Column(
        "created_at",
        nullable=False,
        server_default=text("now()")
    )

    updated_at = Column(
        "updated_at",
        nullable=False,
        server_default=text("now()")
    )

    __table_args__ = (
        CheckConstraint(
            "(user_type != 'admin' OR auth_type = 'password')",
            name="chk_admin_requires_password"
        ),
        CheckConstraint(
            "(auth_type != 'password' OR password_hash IS NOT NULL)",
            name="chk_password_requires_hash"
        ),
    )