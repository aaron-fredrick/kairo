import random
import os
import structlog
from typing import Tuple

from app.core.config import settings
from app.infrastructure.repositories.user_repository import UserRepository
from app.infrastructure.cache.cache_manager import CacheManager
from app.domain.models.user_domain import UserDomain
from app.core.security import create_access_token, create_refresh_token, get_password_hash, verify_password
from jose import jwt, JWTError

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
        logger.debug("Starting unique username generation for anonymous join")
        max_attempts = 10
        for attempt in range(1, max_attempts + 1):
            adj = random.choice(self._adjectives).lower()
            noun = random.choice(self._nouns).lower()
            num = random.randint(1000, 9999)
            username = f"{adj}-{noun}-{num}"
            
            logger.debug("Generated candidate username", candidate=username, attempt=attempt)
            cache_key = f"username_taken:{username}"
            
            # Trust the local cache: if TTL is necessary local TTL is half of actual TTL.
            # CacheManager handles this automatically now.
            # Only checking cache, as per design repo should not be involved in uniqueness check
            exists_in_cache = await self.cache_manager.exists(cache_key)
            if exists_in_cache:
                logger.debug("Username exists in cache, retrying", candidate=username)
                continue
                 
            # Username is unique! Reserve it in cache
            logger.debug("Unique username found and reserved", username=username)
            ttl = settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60
            await self.cache_manager.set(cache_key, "1", ttl=ttl) 
            return username
            
        logger.error("Failed to generate a unique username", max_attempts=max_attempts)
        raise ValueError("Could not generate a unique username")

    def _cache_key_for_user(self, user_id: int) -> str:
        return f"anon_user:{user_id}" if user_id < 0 else f"user:{user_id}"

    def _build_user_domain(self, data: dict) -> UserDomain:
        return UserDomain(
            id=data["id"],
            username=data["username"],
            pfp_hash=data.get("pfp_hash"),
            is_anonymous=data["is_anonymous"],
            is_superadmin=data["is_superadmin"],
            role=data["role"]
        )

    async def _get_user_from_cache(self, user_id: int) -> dict:
        import json
        key = self._cache_key_for_user(user_id)
        raw = await self.cache_manager.get(key)
        if not raw:
            logger.warning("User not found in cache", user_id=user_id)
            raise ValueError("Session expired")
        return json.loads(raw)

    async def _save_user_to_cache(self, user_id: int, user_data: dict, ttl: int) -> None:
        import json
        key = self._cache_key_for_user(user_id)
        await self.cache_manager.set(key, json.dumps(user_data), ttl=ttl)

    async def register(self, username: str, password: str) -> Tuple[UserDomain, str, str]:
        logger.debug("Initiating user registration", username=username)

        username_key = f"user_by_username:{username}"
        if await self.cache_manager.exists(username_key):
            logger.warning("Registration failed: username already taken", username=username)
            raise ValueError("Username is already taken")

        user_id = random.randint(1_000_000, 9_999_999)
        hashed = get_password_hash(password)
        ttl = settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60
        user_data = {
            "id": user_id,
            "username": username,
            "hashed_password": hashed,
            "pfp_hash": None,
            "is_anonymous": False,
            "is_superadmin": False,
            "role": "normal"
        }
        await self._save_user_to_cache(user_id, user_data, ttl)
        await self.cache_manager.set(username_key, str(user_id), ttl=ttl)

        logger.info("User registered in cache successfully", user_id=user_id, username=username)
        user_domain = self._build_user_domain(user_data)
        access_token = create_access_token(subject=str(user_id))
        refresh_token = create_refresh_token(subject=str(user_id))
        return user_domain, access_token, refresh_token

    async def login(self, username: str, password: str) -> Tuple[UserDomain, str, str]:
        import json
        logger.debug("Initiating login", username=username)

        username_key = f"user_by_username:{username}"
        user_id_str = await self.cache_manager.get(username_key)
        if not user_id_str:
            logger.warning("Login failed: user not found in cache", username=username)
            raise ValueError("Invalid credentials")

        user_id = int(user_id_str)
        user_data = await self._get_user_from_cache(user_id)

        hashed_password = user_data.get("hashed_password")
        if not hashed_password or not verify_password(password, hashed_password):
            logger.warning("Login failed: invalid password", username=username)
            raise ValueError("Invalid credentials")

        logger.info("User logged in successfully", user_id=user_id, username=username)
        user_domain = self._build_user_domain(user_data)
        access_token = create_access_token(subject=str(user_id))
        refresh_token = create_refresh_token(subject=str(user_id))
        return user_domain, access_token, refresh_token

    async def get_me(self, user_id: int) -> UserDomain:
        logger.debug("Fetching user profile", user_id=user_id)
        data = await self._get_user_from_cache(user_id)
        return self._build_user_domain(data)


    async def anonymous_join(self) -> Tuple[UserDomain, str, str]:
        logger.debug("Initiating anonymous join flow")
        username = await self._generate_unique_username()
        
        import json
        
        # Create user purely in memory/cache with a negative ID to avoid DB collisions
        user_id = -random.randint(1_000_000, 9_999_999)
        logger.debug("Creating anonymous user in cache", username=username, user_id=user_id)
        
        user_domain = UserDomain(
            id=user_id,
            username=username,
            pfp_hash=None,
            is_anonymous=True,
            is_superadmin=False,
            role="normal"
        )
        
        # TTL matches refresh token expiry exactly, so anonymous user exists as long as they can refresh
        ttl = settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60
        user_data = {
            "id": user_domain.id,
            "username": user_domain.username,
            "pfp_hash": user_domain.pfp_hash,
            "is_anonymous": user_domain.is_anonymous,
            "is_superadmin": user_domain.is_superadmin,
            "role": user_domain.role
        }
        await self.cache_manager.set(
            f"anon_user:{user_id}",
            json.dumps(user_data),
            ttl=ttl
        )
        
        logger.debug("Anonymous user created in cache successfully", user_id=user_id, ttl=ttl)
        
        # Create tokens
        logger.debug("Generating tokens for anonymous user", user_id=user_id)
        access_token = create_access_token(subject=str(user_id))
        refresh_token = create_refresh_token(subject=str(user_id))
        
        logger.debug("Anonymous join flow completed successfully", user_id=user_id)
        return user_domain, access_token, refresh_token

    async def refresh_session(self, refresh_token: str) -> Tuple[str, str]:
        import json
        try:
            payload = jwt.decode(refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            user_id_str = payload.get("sub")
            token_type = payload.get("type")
            
            if not user_id_str or token_type != "refresh":
                logger.error("Invalid refresh token format or type", user_id=user_id_str, type=token_type)
                raise ValueError("Invalid refresh token")
                
            user_id = int(user_id_str)
            
            # If user is anonymous, check cache
            if user_id < 0:
                user_data_str = await self.cache_manager.get(f"anon_user:{user_id}")
                if not user_data_str:
                    logger.warning("Anonymous user cache expired during refresh attempt", user_id=user_id)
                    raise ValueError("Session expired")
                    
                # Extend cache TTL
                ttl = settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60
                await self.cache_manager.set(f"anon_user:{user_id}", user_data_str, ttl=ttl)
                
                # Also extend the username_taken TTL so nobody else can take it
                user_data = json.loads(user_data_str)
                username = user_data.get("username")
                if username:
                    await self.cache_manager.set(f"username_taken:{username}", "1", ttl=ttl)
                    
                logger.debug("Extended anonymous user cache TTL", user_id=user_id)
            else:
                # Registered user — resolve from cache and extend TTL
                ttl = settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60
                user_data = await self._get_user_from_cache(user_id)
                username = user_data.get("username")
                await self._save_user_to_cache(user_id, user_data, ttl)
                if username:
                    await self.cache_manager.set(f"user_by_username:{username}", str(user_id), ttl=ttl)
                logger.debug("Extended registered user cache TTL", user_id=user_id)
            
            new_access_token = create_access_token(subject=str(user_id))
            new_refresh_token = create_refresh_token(subject=str(user_id))
            
            logger.info("Session refreshed successfully", user_id=user_id)
            return new_access_token, new_refresh_token
            
        except JWTError as e:
            logger.error("JWT Error during refresh", error=str(e))
            raise ValueError("Invalid or expired refresh token")
