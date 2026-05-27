import random
import secrets
import string
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_password_hash
from app.core.config import settings
from app.core.logging import get_logger
from app.models.room import Room
from app.models.user import User, UserRole

logger = get_logger(__name__)

SYSTEM_ROOM_ADMIN = "admins"
SYSTEM_ROOM_MODS = "moderators"

# Loaded lazily from the auth_service word lists via the factory below.
_adjectives: list[str] = []


def _load_adjectives() -> list[str]:
    """Return the shared adjective list, bootstrapping from config files on first call."""
    global _adjectives
    if _adjectives:
        return _adjectives

    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    adj_path = os.path.join(base_dir, settings.ADJECTIVES_FILE)
    try:
        with open(adj_path, "r", encoding="utf-8") as f:
            _adjectives = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        _adjectives = ["anonymous", "mystic", "swift", "bold", "calm"]
        logger.warning("Adjectives file not found at '%s'. Using built-in fallback.", adj_path)
    return _adjectives


def _generate_role_username(role: UserRole) -> str:
    """Generate an {adjective}-{role} username for named (non-anonymous) accounts."""
    adjectives = _load_adjectives()
    adj = random.choice(adjectives)
    return f"{adj}-{role.value}"


def generate_random_password(length: int = 16) -> str:
    """Generate a cryptographically secure random plaintext password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class AdminService:
    async def _ensure_unique_username(
        self, db: AsyncSession, role: UserRole, max_attempts: int = 50
    ) -> str:
        """Attempt to generate a unique adjective-role username not already in the DB."""
        for _ in range(max_attempts):
            candidate = _generate_role_username(role)
            result = await db.execute(select(User).where(User.username == candidate))
            if result.scalars().first() is None:
                return candidate

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not generate a unique username. Try again later.",
        )

    async def create_named_user(
        self,
        db: AsyncSession,
        role: UserRole,
        plain_password: Optional[str] = None,
    ) -> Tuple[User, str]:
        """
        Create a new admin or moderator user.

        Returns the created User ORM object and the plaintext password that was
        used (so callers can briefly surface it to the creating admin). When no
        password is supplied a random one is generated.
        """
        if role not in (UserRole.ADMIN, UserRole.MODERATOR):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Named users must have the 'admin' or 'moderator' role.",
            )

        password = plain_password if plain_password else generate_random_password()
        username = await self._ensure_unique_username(db, role)

        user = User(
            username=username,
            hashed_password=get_password_hash(password),
            is_anonymous=False,
            role=role.value,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info("Named user created: username='%s' role='%s'", username, role.value)
        return user, password

    async def seed_default_admin(self, db: AsyncSession) -> None:
        """
        Ensure the built-in 'admin' user exists. Creates it with the password
        sourced from settings.ADMIN_PASSWORD (env var ADMIN_PASSWORD, default 'admin').
        """
        result = await db.execute(select(User).where(User.username == "admin"))
        if result.scalars().first() is not None:
            logger.debug("Default admin user already exists — skipping seed.")
            return

        admin = User(
            username="admin",
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            is_anonymous=False,
            is_superadmin=True,
            role=UserRole.ADMIN.value,
        )
        db.add(admin)
        await db.commit()
        logger.info("Default admin user seeded (username='admin').")

    async def seed_system_rooms(self, db: AsyncSession) -> None:
        """
        Ensure the two privileged system rooms exist:
          - 'admins'      — visible and writable only by admins
          - 'moderators'  — visible and writable by admins and moderators
        """
        for name, description in (
            ("public", "Public discussion channel"),
            (SYSTEM_ROOM_ADMIN, "Private admin-only channel"),
            (SYSTEM_ROOM_MODS, "Private channel for admins and moderators"),
        ):
            result = await db.execute(select(Room).where(Room.name == name))
            if result.scalars().first() is None:
                room = Room(name=name, description=description)
                db.add(room)
                logger.info("System room '%s' created.", name)

        await db.commit()


admin_service = AdminService()
