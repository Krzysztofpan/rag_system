from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import WatchError

from app.services.chat.protocol import ProtocolEvent

_META = "rag:run:{conversation_id}:meta"
_EVENTS = "rag:run:{conversation_id}:events"
_SUBS = "rag:run:{conversation_id}:subs"
_CHANNEL = "rag:run:{conversation_id}:ch"
_STARTED = "rag:run:{conversation_id}:started"
_CONTROL = "rag:run:{conversation_id}:ctl"


class RedisRunStore:
    def __init__(self, redis: Redis, *, replay_limit: int) -> None:
        self.redis = redis
        self.replay_limit = replay_limit

    @staticmethod
    def meta_key(conversation_id: UUID) -> str:
        return _META.format(conversation_id=conversation_id)

    @staticmethod
    def events_key(conversation_id: UUID) -> str:
        return _EVENTS.format(conversation_id=conversation_id)

    @staticmethod
    def subs_key(conversation_id: UUID) -> str:
        return _SUBS.format(conversation_id=conversation_id)

    @staticmethod
    def channel(conversation_id: UUID) -> str:
        return _CHANNEL.format(conversation_id=conversation_id)

    @staticmethod
    def started_channel(conversation_id: UUID) -> str:
        return _STARTED.format(conversation_id=conversation_id)

    @staticmethod
    def control_channel(conversation_id: UUID) -> str:
        return _CONTROL.format(conversation_id=conversation_id)

    async def try_acquire(
        self,
        conversation_id: UUID,
        run_id: str,
    ) -> bool:
        meta_key = self.meta_key(conversation_id)
        events_key = self.events_key(conversation_id)
        subs_key = self.subs_key(conversation_id)
        payload = json.dumps(
            {"run_id": run_id, "finished": False, "seq": 0},
            separators=(",", ":"),
        )
        async with self.redis.pipeline() as pipe:
            while True:
                try:
                    await pipe.watch(meta_key)
                    raw = await self.redis.get(meta_key)
                    if raw is not None:
                        meta = json.loads(raw)
                        if not meta.get("finished"):
                            await pipe.reset()
                            return False
                    pipe.multi()
                    pipe.set(meta_key, payload)
                    pipe.delete(events_key, subs_key)
                    pipe.publish(self.started_channel(conversation_id), run_id)
                    await pipe.execute()
                    return True
                except WatchError:
                    continue

    async def load_meta(self, conversation_id: UUID) -> dict[str, Any] | None:
        raw = await self.redis.get(self.meta_key(conversation_id))
        if raw is None:
            return None
        return json.loads(raw)

    async def append_event(
        self,
        conversation_id: UUID,
        run_id: str,
        event: ProtocolEvent,
        *,
        finished: bool,
    ) -> None:
        payload = json.dumps(event, separators=(",", ":"))
        meta = json.dumps(
            {
                "run_id": run_id,
                "finished": finished,
                "seq": event["seq"],
            },
            separators=(",", ":"),
        )
        async with self.redis.pipeline(transaction=False) as pipe:
            pipe.rpush(self.events_key(conversation_id), payload)
            pipe.ltrim(self.events_key(conversation_id), -self.replay_limit, -1)
            pipe.set(self.meta_key(conversation_id), meta)
            pipe.publish(self.channel(conversation_id), payload)
            await pipe.execute()

    async def list_events(self, conversation_id: UUID) -> list[ProtocolEvent]:
        raw_events = await self.redis.lrange(self.events_key(conversation_id), 0, -1)
        return [json.loads(raw) for raw in raw_events]

    async def add_subscriber(self, conversation_id: UUID, subscription_id: str) -> None:
        await self.redis.sadd(self.subs_key(conversation_id), subscription_id)

    async def remove_subscriber(
        self,
        conversation_id: UUID,
        subscription_id: str,
    ) -> int:
        await self.redis.srem(self.subs_key(conversation_id), subscription_id)
        return int(await self.redis.scard(self.subs_key(conversation_id)))

    async def subscriber_count(self, conversation_id: UUID) -> int:
        return int(await self.redis.scard(self.subs_key(conversation_id)))

    async def notify_control(self, conversation_id: UUID, message: str) -> None:
        await self.redis.publish(self.control_channel(conversation_id), message)

    async def delete_if_run(
        self,
        conversation_id: UUID,
        run_id: str,
    ) -> None:
        meta_key = self.meta_key(conversation_id)
        async with self.redis.pipeline() as pipe:
            while True:
                try:
                    await pipe.watch(meta_key)
                    raw = await self.redis.get(meta_key)
                    if raw is None:
                        await pipe.reset()
                        return
                    meta = json.loads(raw)
                    if meta.get("run_id") != run_id:
                        await pipe.reset()
                        return
                    pipe.multi()
                    pipe.delete(
                        meta_key,
                        self.events_key(conversation_id),
                        self.subs_key(conversation_id),
                    )
                    await pipe.execute()
                    return
                except WatchError:
                    continue
