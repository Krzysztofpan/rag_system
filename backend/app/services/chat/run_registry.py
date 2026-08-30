"""Run storage.

`InMemoryRunRegistry` is for unit tests and local uvicorn without Redis.
Compose and production use `RedisRunRegistry` so command and stream can
land on different processes. The agent `asyncio.Task` still lives only in
the process that accepted `run.start`.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Protocol
from uuid import UUID

from app.services.chat.run_session import RunSession

RunFactory = Callable[[RunSession], Awaitable[None]]


class RunRegistry(Protocol):
    replay_limit: int
    subscriber_timeout_seconds: float
    disconnect_grace_seconds: float
    finished_ttl_seconds: float

    async def start(
        self,
        conversation_id: UUID,
        run_id: str,
        run_factory: RunFactory,
    ) -> RunSession: ...

    async def get(self, conversation_id: UUID) -> RunSession | None: ...

    async def wait_for_session_after(
        self,
        conversation_id: UUID,
        previous: RunSession,
        *,
        timeout: float,
    ) -> RunSession | None: ...

    async def remove_if_current(
        self,
        conversation_id: UUID,
        session: RunSession,
    ) -> None: ...

    async def close(self) -> None: ...


class InMemoryRunRegistry:
    def __init__(
        self,
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
        self._sessions: dict[UUID, RunSession] = {}
        self._lock = asyncio.Lock()
        self._session_changed = asyncio.Condition(self._lock)

    async def start(
        self,
        conversation_id: UUID,
        run_id: str,
        run_factory: RunFactory,
    ) -> RunSession:
        async with self._session_changed:
            existing = self._sessions.get(conversation_id)
            if existing is not None and not existing.finished:
                raise RuntimeError("A run is already active for this conversation")

            session = RunSession(
                conversation_id=conversation_id,
                run_id=run_id,
                registry=self,
                replay_limit=self.replay_limit,
            )
            self._sessions[conversation_id] = session
            self._session_changed.notify_all()
            session.task = asyncio.create_task(run_factory(session))
            session.arm_initial_subscriber_timeout(self.subscriber_timeout_seconds)
            return session

    async def get(self, conversation_id: UUID) -> RunSession | None:
        async with self._lock:
            return self._sessions.get(conversation_id)

    async def wait_for_session_after(
        self,
        conversation_id: UUID,
        previous: RunSession,
        *,
        timeout: float,
    ) -> RunSession | None:
        def next_session() -> RunSession | None:
            session = self._sessions.get(conversation_id)
            if session is None or session.run_id == previous.run_id:
                return None
            return session

        async with self._session_changed:
            session = next_session()
            if session is not None:
                return session
            try:
                await asyncio.wait_for(
                    self._session_changed.wait_for(
                        lambda: next_session() is not None
                    ),
                    timeout=timeout,
                )
            except TimeoutError:
                return None
            return next_session()

    async def remove_if_current(
        self,
        conversation_id: UUID,
        session: RunSession,
    ) -> None:
        async with self._lock:
            if self._sessions.get(conversation_id) is session:
                self._sessions.pop(conversation_id, None)

    async def close(self) -> None:
        async with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            if session.task is not None and not session.task.done():
                session.task.cancel()
        for session in sessions:
            if session.task is not None:
                with suppress(asyncio.CancelledError):
                    await session.task
