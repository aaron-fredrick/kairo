"""MockRedis in-memory client."""
import time

import pytest

from app_backend.db.redis import MockRedis


@pytest.fixture
async def redis():
    return MockRedis()


@pytest.mark.asyncio
async def test_zset_operations(redis):
    future = int(time.time()) + 3600
    await redis.zadd("active_users", {"alice": future})
    assert await redis.zscore("active_users", "alice") == future
    assert await redis.zcard("active_users") == 1
    active = await redis.zrangebyscore("active_users", min=time.time(), max="+inf")
    assert active == ["alice"]
    removed = await redis.zremrangebyscore("active_users", "-inf", time.time() - 1)
    assert removed == 0


@pytest.mark.asyncio
async def test_hash_operations(redis):
    count = await redis.hincrby("room:1:presence_count", "bob", 2)
    assert count == 2
    keys = await redis.hkeys("room:1:presence_count")
    assert keys == ["bob"]
    deleted = await redis.hdel("room:1:presence_count", "bob")
    assert deleted == 1
    assert await redis.hkeys("room:1:presence_count") == []
