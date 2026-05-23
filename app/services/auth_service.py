import os
import random
import time
from typing import Tuple, List
from fastapi import HTTPException, status
from redis.asyncio import Redis
from app.core.config import settings
from app.auth.jwt import create_access_token

class AuthService:
    def __init__(self):
        self.adjectives: List[str] = []
        self.nouns: List[str] = []
        self._load_words()

    def _load_words(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        adj_path = os.path.join(base_dir, settings.ADJECTIVES_FILE)
        noun_path = os.path.join(base_dir, settings.NOUNS_FILE)

        try:
            with open(adj_path, 'r', encoding='utf-8') as f:
                self.adjectives = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            self.adjectives = ["anonymous", "mystic", "swift"]

        try:
            with open(noun_path, 'r', encoding='utf-8') as f:
                self.nouns = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            self.nouns = ["fox", "bear", "wolf"]

    @property
    def total_permutations(self) -> int:
        return len(self.adjectives) * len(self.nouns)

    @property
    def max_users(self) -> int:
        if settings.USER_LIMIT is not None:
            return min(settings.USER_LIMIT, self.total_permutations)
        return self.total_permutations

    async def _cleanup_expired_users(self, redis: Redis):
        current_time = int(time.time())
        await redis.zremrangebyscore("active_users", "-inf", current_time)

    async def get_active_users_count(self, redis: Redis) -> int:
        await self._cleanup_expired_users(redis)
        return await redis.zcard("active_users")

    async def generate_unique_username(self, redis: Redis) -> str:
        active_count = await self.get_active_users_count(redis)
        
        if active_count >= self.max_users:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Server is full, please try again later."
            )

        current_time = int(time.time())
        max_attempts = 100
        
        for _ in range(max_attempts):
            adj = random.choice(self.adjectives)
            noun = random.choice(self.nouns)
            username = f"{adj}-{noun}"
            
            score = await redis.zscore("active_users", username)
            if score is None or score < current_time:
                # Available!
                return username
                
        # Fallback if random fails due to high load (though unlikely unless very full)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not generate a unique username, please try again."
        )

    async def join_server(self, redis: Redis, password: str = None) -> Tuple[str, str]:
        """Validates password, generates username, registers it, and returns token."""
        if settings.SERVER_PASSWORD:
            if not password or password != settings.SERVER_PASSWORD:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid server password."
                )

        username = await self.generate_unique_username(redis)
        
        # Register in Redis sorted set
        expire_time = int(time.time()) + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        await redis.zadd("active_users", {username: expire_time})
        
        # Generate JWT Token
        access_token = create_access_token(data={"sub": username})
        
        return username, access_token

    async def refresh_user_activity(self, redis: Redis, username: str):
        """Update the expiration time of the user if they are active."""
        score = await redis.zscore("active_users", username)
        if score is not None:
            expire_time = int(time.time()) + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
            await redis.zadd("active_users", {username: expire_time})

auth_service = AuthService()
