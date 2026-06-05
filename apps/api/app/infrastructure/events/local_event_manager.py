from collections import defaultdict
from typing import Callable, Any, DefaultDict, List


class LocalEventManager:
    def __init__(self):
        self._handlers: DefaultDict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: Callable[..., Any]) -> None:
        self._handlers[event_name].append(handler)

    async def emit(self, event_name: str, payload: Any) -> None:
        for handler in self._handlers.get(event_name, []):
            result = handler(payload)

            if hasattr(result, "__await__"):
                await result