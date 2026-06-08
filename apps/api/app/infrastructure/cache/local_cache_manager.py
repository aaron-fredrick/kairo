import time
from collections import OrderedDict
from typing import Any


class LocalCacheManager:

    def __init__(self, max_size: int = 128):
        self._cache: OrderedDict[str, tuple[Any, float | None]] = OrderedDict()
        self._max_size = max_size

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

    def _evict_lru(self) -> None:
        if len(self._cache) >= self._max_size:
            # Remove the least recently used item (first item in OrderedDict)
            self._cache.popitem(last=False)

    async def get(self, key: str) -> Any | None:
        if self._is_expired(key):
            return None

        value, _ = self._cache[key]
        # Move to end to mark as most recently used
        self._cache.move_to_end(key)
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

        # Remove if exists to re-insert at the end
        if key in self._cache:
            del self._cache[key]
        else:
            self._evict_lru()

        self._cache[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    async def exists(self, key: str) -> bool:
        return not self._is_expired(key)
    