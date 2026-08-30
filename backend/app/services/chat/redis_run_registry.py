from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from uuid import UUID

from redis.asyncio import Redis

from app.services.chat.redis_store import RedisRunStore
from app.services.chat.run_session import RunSession

RunFactory = Callable[[RunSession], Awaitable[None]]


class RedisRunRegistry:
    def __init__(
        self,
        redis: Redis,
        *,
        replay_limit: int = 2000,
        subscriber_timeout_seconds: float = 10,
        disconnect_grace_seconds: float = 1,
        finished_ttl_seconds: float = 30,
    ) -> None:
        self.replay_limit = replay_limit
        self.subscriber_timeout_seconds = subscriber_timeout_seconds
        self.disconnect_grace_seconds = disconnect_grace_seconds
        self.finished_ttl_seconds = finished_ttl_seconds
        self._store = RedisRunStore(redis, replay_limit=replay_limit)
        self._owned: dict[UUID, RunSession] = {}
        self._known: dict[tuple[UUID, str], RunSession] = {}
        self._lock = asyncio.Lock()

    async def start(
        self,
        conversation_id: UUID,
        run_id: str,
        run_factory: RunFactory,
    ) -> RunSession:
        acquired = await self._store.try_acquire(conversation_id, run_id)
        if not acquired:
            raise RuntimeError("A run is already active for this conversation")

        async with self._lock:
            session = RunSession(
                conversation_id=conversation_id,
                run_id=run_id,
                registry=self,
                replay_limit=self.replay_limit,
                event_store=self._store,
            )
            self._owned[conversation_id] = session
            self._known[(conversation_id, run_id)] = session
            session.task = asyncio.create_task(run_factory(session))
            session.arm_initial_subscriber_timeout(self.subscriber_timeout_seconds)
            return session

    async def get(self, conversation_id: UUID) -> RunSession | None:
        async with self._lock:
            owned = self._owned.get(conversation_id)
            if owned is not None:
                return owned
        meta = await self._store.load_meta(conversation_id)
        if meta is None:
            return None
        return await self._remote_session(conversation_id, str(meta["run_id"]), meta)

    async def wait_for_session_after(
        self,
        conversation_id: UUID,
        previous: RunSession,
        *,
        timeout: float,
    ) -> RunSession | None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        pubsub = self._store.redis.pubsub()
        await pubsub.subscribe(self._store.started_channel(conversation_id))
        try:
            while True:
                session = await self.get(conversation_id)
                if session is not None and session.run_id != previous.run_id:
                    return session
                remaining = deadline - loop.time()
                if remaining <= 0:
                    return None
                await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=min(remaining, 1.0),
                )
        finally:
            await pubsub.unsubscribe()
            await pubsub.aclose()

    async def remove_if_current(
        self,
        conversation_id: UUID,
        session: RunSession,
    ) -> None:
        await self._store.delete_if_run(conversation_id, session.run_id)
        async with self._lock:
            if self._owned.get(conversation_id) is session:
                self._owned.pop(conversation_id, None)
            self._known.pop((conversation_id, session.run_id), None)

    async def close(self) -> None:
        async with self._lock:
            sessions = list(self._owned.values())
            self._owned.clear()
            self._known.clear()
        for session in sessions:
            await session.close_background()
            if session.task is not None and not session.task.done():
                session.task.cancel()
        for session in sessions:
            if session.task is not None:
                with suppress(asyncio.CancelledError):
                    await session.task

    async def _remote_session(
        self,
        conversation_id: UUID,
        run_id: str,
        meta: dict,
    ) -> RunSession:
        key = (conversation_id, run_id)
        async with self._lock:
            existing = self._known.get(key)
            if existing is not None:
                existing.finished = bool(meta.get("finished"))
                return existing
            session = RunSession(
                conversation_id=conversation_id,
                run_id=run_id,
                registry=self,
                replay_limit=self.replay_limit,
                event_store=self._store,
                remote=True,
                finished=bool(meta.get("finished")),
                seq=int(meta.get("seq") or 0),
            )
            self._known[key] = session
            return session
