import random
import os
import structlog
from typing import Tuple

from app.core.config import settings
from app.infrastructure.repositories.user_repository import UserRepository
from app.infrastructure.cache.cache_manager import CacheManager
from app.domain.models.user_domain import UserDomain
from app.core.security import create_access_token

logger = structlog.get_logger(__name__)

class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        cache_manager: CacheManager
    ):
        self.user_repo = user_repo
        self.cache_manager = cache_manager
        self._adjectives = self._load_words(settings.ADJECTIVES_FILE, ["Happy", "Brave", "Clever", "Swift", "Silent"])
        self._nouns = self._load_words(settings.NOUNS_FILE, ["Panda", "Fox", "Tiger", "Eagle", "Wolf"])

    def _load_words(self, filepath: str, defaults: list[str]) -> list[str]:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                words = [line.strip() for line in f if line.strip()]
                if words:
                    return words
        return defaults

    async def _generate_unique_username(self) -> str:
        max_attempts = 10
        for _ in range(max_attempts):
            adj = random.choice(self._adjectives).capitalize()
            noun = random.choice(self._nouns).capitalize()
            num = random.randint(1000, 9999)
            username = f"{adj}{noun}{num}"
            
            cache_key = f"username_taken:{username}"
            
            # Trust the local cache: if TTL is necessary local TTL is half of actual TTL.
            # CacheManager handles this automatically now.
            exists_in_cache = await self.cache_manager.exists(cache_key)
            if exists_in_cache:
                continue
                
            # Check DB to be absolutely sure for cold cache.
            existing_user = await self.user_repo.get_by_username(username)
            if existing_user:
                 await self.cache_manager.set(cache_key, "1", ttl=86400) # Reserve it in cache
                 continue
                 
            # Username is unique! Reserve it in cache
            await self.cache_manager.set(cache_key, "1", ttl=86400) 
            return username
            
        raise ValueError("Could not generate a unique username")

    async def anonymous_join(self) -> Tuple[UserDomain, str]:
        username = await self._generate_unique_username()
        
        # Create user
        user_dto = await self.user_repo.create({
            "username": username,
            "is_anonymous": True,
            "role": "normal"
        })
        
        user_domain = UserDomain(
            id=user_dto.id,
            username=user_dto.username,
            pfp_hash=user_dto.pfp_hash,
            is_anonymous=user_dto.is_anonymous,
            is_superadmin=user_dto.is_superadmin,
            role=user_dto.role
        )
        
        # Create token
        token = create_access_token(subject=str(user_dto.id))
        
        return user_domain, token
