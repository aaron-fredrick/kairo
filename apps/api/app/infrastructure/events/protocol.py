from typing import Protocol, Callable, Any


class EventProtocol(Protocol):

    def subscribe(self, event_name: str, handler: Callable[..., Any]) -> None:
        ...

    async def emit(self, event_name: str, payload: Any) -> None:
        ...