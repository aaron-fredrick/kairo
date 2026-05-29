"""Background workers."""
import pytest

from app_backend.workers.broadcast import BroadcastJob, _process_broadcast


@pytest.mark.asyncio
async def test_process_broadcast_publishes(monkeypatch):
    published: list[tuple[str, str]] = []

    class FakeBus:
        async def publish(self, channel: str, message: str) -> None:
            published.append((channel, message))

    monkeypatch.setattr("app_backend.core.event_bus.event_bus", FakeBus())
    job = BroadcastJob(room_id=3, event_type="ping", payload={"x": 1})
    await _process_broadcast(job)
    assert published[0][0] == "room:3:events"
    assert "ping" in published[0][1]
