from typing import Any, Protocol


class CacheProtocol(Protocol):

    async def get(self, key: str) -> Any | None:
        ...

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        ...

    async def delete(self, key: str) -> None:
        ...

    async def exists(self, key: str) -> bool:
        ...