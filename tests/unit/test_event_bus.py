"""In-memory event bus."""
import pytest

from app.core.event_bus import LocalEventBus


@pytest.mark.asyncio
async def test_publish_delivers_to_subscriber():
    bus = LocalEventBus()
    received: list[str] = []

    async def handler(msg: str) -> None:
        received.append(msg)

    await bus.subscribe("room:1:events", handler)
    await bus.publish("room:1:events", '{"event":"ping"}')
    assert received == ['{"event":"ping"}']


@pytest.mark.asyncio
async def test_publish_unknown_channel_is_noop():
    bus = LocalEventBus()
    await bus.publish("missing", "data")


@pytest.mark.asyncio
async def test_close_clears_subscribers():
    bus = LocalEventBus()
    await bus.subscribe("c", lambda m: None)
    await bus.close()
    await bus.publish("c", "x")  # no handlers
