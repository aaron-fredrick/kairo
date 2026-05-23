import os
import random
import time
from typing import Optional, Tuple, List

from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.core.config import settings
from app.core.logging import get_logger
from app.auth.jwt import create_access_token

logger = get_logger(__name__)


class AuthService:
    def __init__(self) -> None:
        self.adjectives: List[str] = []
        self.nouns: List[str] = []
        self._load_words()

    def _load_words(self) -> None:
        """Load adjective and noun word lists from the configured text files."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        adj_path = os.path.join(base_dir, settings.ADJECTIVES_FILE)
        noun_path = os.path.join(base_dir, settings.NOUNS_FILE)

        try:
            with open(adj_path, "r", encoding="utf-8") as f:
                self.adjectives = [line.strip() for line in f if line.strip()]
            logger.debug("Loaded %d adjectives from '%s'", len(self.adjectives), adj_path)
        except FileNotFoundError:
            self.adjectives = ["anonymous", "mystic", "swift"]
            logger.warning("Adjectives file not found at '%s'. Using built-in fallback list.", adj_path)

        try:
            with open(noun_path, "r", encoding="utf-8") as f:
                self.nouns = [line.strip() for line in f if line.strip()]
            logger.debug("Loaded %d nouns from '%s'", len(self.nouns), noun_path)
        except FileNotFoundError:
            self.nouns = ["fox", "bear", "wolf"]
            logger.warning("Nouns file not found at '%s'. Using built-in fallback list.", noun_path)

        logger.info(
            "Username pool ready: %d adjectives × %d nouns = %d permutations (max_users=%d)",
            len(self.adjectives),
            len(self.nouns),
            self.total_permutations,
            self.max_users,
        )

    @property
    def total_permutations(self) -> int:
        return len(self.adjectives) * len(self.nouns)

    @property
    def max_users(self) -> int:
        if settings.USER_LIMIT is not None:
            return min(settings.USER_LIMIT, self.total_permutations)
        return self.total_permutations

    async def _cleanup_expired_users(self, redis: Redis) -> None:
        """Remove all users whose session score has fallen below the current epoch time."""
        current_time = int(time.time())
        removed = await redis.zremrangebyscore("active_users", "-inf", current_time)
        if removed:
            logger.debug("Evicted %d expired user session(s) from active_users set", removed)

    async def get_active_users_count(self, redis: Redis) -> int:
        """Return the current count of non-expired active users."""
        await self._cleanup_expired_users(redis)
        count = await redis.zcard("active_users")
        logger.debug("Active user count: %d / %d", count, self.max_users)
        return count

    async def generate_unique_username(self, redis: Redis) -> str:
        """
        Randomly sample adjective-noun pairs until a non-active one is found.

        Raises HTTP 503 when the server is at capacity or exhausts sampling attempts.
        """
        active_count = await self.get_active_users_count(redis)

        if active_count >= self.max_users:
            logger.warning(
                "Server at capacity: %d / %d active users", active_count, self.max_users
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Server is full, please try again later.",
            )

        current_time = int(time.time())
        max_attempts = 100

        for attempt in range(1, max_attempts + 1):
            adj = random.choice(self.adjectives)
            noun = random.choice(self.nouns)
            candidate = f"{adj}-{noun}"

            score = await redis.zscore("active_users", candidate)
            if score is None or score < current_time:
                logger.debug("Username '%s' allocated after %d attempt(s)", candidate, attempt)
                return candidate

        logger.error(
            "Failed to allocate a unique username after %d attempts (active=%d, max=%d)",
            max_attempts,
            active_count,
            self.max_users,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not generate a unique username, please try again.",
        )

    async def join_server(
        self, redis: Redis, password: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Validate the server password (if set), allocate a username, register it in
        Redis, and return a (username, access_token) pair.
        """
        if settings.SERVER_PASSWORD:
            if not password or password != settings.SERVER_PASSWORD:
                logger.warning("Failed join attempt: incorrect server password supplied")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid server password.",
                )

        username = await self.generate_unique_username(redis)

        expire_time = int(time.time()) + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        await redis.zadd("active_users", {username: expire_time})

        access_token = create_access_token(data={"sub": username})

        logger.info("New session started for '%s' (expires at epoch %d)", username, expire_time)
        return username, access_token

    async def refresh_user_activity(self, redis: Redis, username: str) -> None:
        """Slide the session expiry window forward for an active user."""
        score = await redis.zscore("active_users", username)
        if score is not None:
            expire_time = int(time.time()) + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
            await redis.zadd("active_users", {username: expire_time})
            logger.debug("Session refreshed for '%s' (new expiry epoch %d)", username, expire_time)


auth_service = AuthService()
