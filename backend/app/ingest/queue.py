from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, TypeAdapter
from redis.asyncio import Redis

INGEST_QUEUE_KEY = "rag:ingest:jobs"


class DocumentIngestJob(BaseModel):
    kind: Literal["document"] = "document"
    conversation_id: UUID
    document_id: UUID
    user_id: UUID
    path: str
    filename: str
    content_type: str | None = None


class YoutubeIngestJob(BaseModel):
    kind: Literal["youtube"] = "youtube"
    conversation_id: UUID
    document_id: UUID
    user_id: UUID
    url: str
    video_id: str


IngestJob = Annotated[
    DocumentIngestJob | YoutubeIngestJob,
    Field(discriminator="kind"),
]

_job_adapter = TypeAdapter(IngestJob)


class IngestQueue:
    def __init__(
        self,
        redis: Redis,
        *,
        key: str = INGEST_QUEUE_KEY,
    ) -> None:
        self._redis = redis
        self.key = key

    async def enqueue(self, job: DocumentIngestJob | YoutubeIngestJob) -> None:
        await self._redis.lpush(self.key, job.model_dump_json())

    async def dequeue(
        self,
        timeout: int = 5,
    ) -> DocumentIngestJob | YoutubeIngestJob | None:
        item = await self._redis.brpop(self.key, timeout=timeout)
        if item is None:
            return None
        _queue_key, payload = item
        return _job_adapter.validate_json(payload)
