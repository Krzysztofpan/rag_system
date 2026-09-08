from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fakeredis import FakeAsyncRedis
from pydantic import ValidationError
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.studio.queue import NoteTitleJob, StudioQueue


@pytest.fixture
async def redis():
    client = FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()


async def test_note_title_job_roundtrip(redis):
    queue = StudioQueue(redis)
    job = NoteTitleJob(
        conversation_id=uuid4(),
        resource_id=uuid4(),
        user_id=uuid4(),
    )

    await queue.enqueue(job)
    loaded = await queue.dequeue(timeout=1)

    assert loaded == job


async def test_dequeue_empty_queue_returns_none(redis):
    queue = StudioQueue(redis)
    assert await queue.dequeue(timeout=1) is None


async def test_dequeue_socket_timeout_returns_none():
    redis = AsyncMock()
    redis.brpop = AsyncMock(side_effect=RedisTimeoutError("Timeout reading from redis"))
    queue = StudioQueue(redis)
    assert await queue.dequeue(timeout=5) is None


async def test_unknown_job_kind_is_rejected(redis):
    queue = StudioQueue(redis)
    await redis.lpush(queue.key, '{"kind":"mind_map","resource_id":"x"}')
    with pytest.raises(ValidationError):
        await queue.dequeue(timeout=1)
