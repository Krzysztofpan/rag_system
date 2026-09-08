from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, TypeAdapter
from redis.asyncio import Redis
from redis.exceptions import TimeoutError as RedisTimeoutError

STUDIO_QUEUE_KEY = "rag:studio:jobs"


class NoteTitleJob(BaseModel):
    kind: Literal["note_title"] = "note_title"
    conversation_id: UUID
    resource_id: UUID
    user_id: UUID


StudioJob = Annotated[
    NoteTitleJob,
    Field(discriminator="kind"),
]

_job_adapter = TypeAdapter(StudioJob)


class StudioQueue:
    def __init__(
        self,
        redis: Redis,
        *,
        key: str = STUDIO_QUEUE_KEY,
    ) -> None:
        self._redis = redis
        self.key = key

    async def enqueue(self, job: NoteTitleJob) -> None:
        await self._redis.lpush(self.key, job.model_dump_json())

    async def dequeue(
        self,
        timeout: int = 5,
    ) -> NoteTitleJob | None:
        try:
            item = await self._redis.brpop(self.key, timeout=timeout)
        except RedisTimeoutError:
            return None
        if item is None:
            return None
        _queue_key, payload = item
        return _job_adapter.validate_json(payload)
