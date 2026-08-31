from uuid import uuid4

import pytest
from fakeredis import FakeAsyncRedis
from pydantic import ValidationError

from app.ingest.queue import DocumentIngestJob, IngestQueue, YoutubeIngestJob


@pytest.fixture
async def redis():
    client = FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()


async def test_document_job_roundtrip(redis):
    queue = IngestQueue(redis)
    job = DocumentIngestJob(
        conversation_id=uuid4(),
        document_id=uuid4(),
        user_id=uuid4(),
        path="/var/rag/uploads/note.md",
        filename="note.md",
        content_type="text/markdown",
    )

    await queue.enqueue(job)
    loaded = await queue.dequeue(timeout=1)

    assert loaded == job


async def test_youtube_job_roundtrip(redis):
    queue = IngestQueue(redis)
    job = YoutubeIngestJob(
        conversation_id=uuid4(),
        document_id=uuid4(),
        user_id=uuid4(),
        url="https://www.youtube.com/watch?v=dQw4w9wgXcQ",
        video_id="dQw4w9wgXcQ",
    )

    await queue.enqueue(job)
    loaded = await queue.dequeue(timeout=1)

    assert loaded == job


async def test_dequeue_empty_queue_returns_none(redis):
    queue = IngestQueue(redis)
    assert await queue.dequeue(timeout=1) is None


async def test_unknown_job_kind_is_rejected(redis):
    queue = IngestQueue(redis)
    await redis.lpush(queue.key, '{"kind":"audio","document_id":"x"}')
    with pytest.raises(ValidationError):
        await queue.dequeue(timeout=1)
