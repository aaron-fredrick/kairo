import time
from typing import Any


class LocalCacheManager:

    def __init__(self):
        self._cache: dict[str, tuple[Any, float | None]] = {}

    def _is_expired(self, key: str) -> bool:
        item = self._cache.get(key)

        if item is None:
            return True

        _, expires_at = item

        if expires_at is None:
            return False

        if time.time() >= expires_at:
            del self._cache[key]
            return True

        return False

    async def get(self, key: str) -> Any | None:
        if self._is_expired(key):
            return None

        value, _ = self._cache[key]
        return value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:

        expires_at = None

        if ttl is not None:
            expires_at = time.time() + ttl

        self._cache[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    async def exists(self, key: str) -> bool:
        return not self._is_expired(key)
    