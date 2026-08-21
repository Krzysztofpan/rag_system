from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from app.services.chat.protocol import (
    ProtocolEvent,
    event_matches,
    is_terminal_event,
)

if TYPE_CHECKING:
    from app.services.chat.run_registry import InMemoryRunRegistry

_STREAM_END = object()
_HEARTBEAT = object()


@dataclass(eq=False)
class RunSubscription:
    session: RunSession
    queue: asyncio.Queue[ProtocolEvent | object]
    replay: list[ProtocolEvent]
    channels: set[str]
    namespaces: list[list[str]] | None
    depth: int | None

    async def events(self) -> AsyncIterator[ProtocolEvent | object]:
        try:
            for event in self.replay:
                yield event
            if self.session.finished:
                return

            while True:
                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout=5)
                except TimeoutError:
                    yield _HEARTBEAT
                    continue
                if item is _STREAM_END:
                    return
                if event_matches(
                    item,
                    channels=self.channels,
                    namespaces=self.namespaces,
                    depth=self.depth,
                ):
                    yield item
        finally:
            await self.session.unsubscribe(self)


@dataclass
class RunSession:
    conversation_id: UUID
    run_id: str
    registry: InMemoryRunRegistry
    replay_limit: int
    task: asyncio.Task[None] | None = None
    events_buffer: deque[ProtocolEvent] = field(init=False)
    subscribers: set[RunSubscription] = field(default_factory=set)
    seq: int = 0
    finished: bool = False
    had_subscriber: bool = False
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _orphan_task: asyncio.Task[None] | None = None
    _cleanup_task: asyncio.Task[None] | None = None

    def __post_init__(self) -> None:
        self.events_buffer = deque(maxlen=self.replay_limit)

    async def publish(self, event: ProtocolEvent) -> ProtocolEvent:
        async with self._lock:
            self.seq += 1
            emitted = {
                **event,
                "type": "event",
                "event_id": f"{self.run_id}:{self.seq}",
                "seq": self.seq,
            }
            self.events_buffer.append(emitted)
            terminal = is_terminal_event(emitted)
            if terminal:
                self.finished = True
            subscribers = list(self.subscribers)

        for subscription in subscribers:
            subscription.queue.put_nowait(emitted)
            if terminal:
                subscription.queue.put_nowait(_STREAM_END)

        if terminal:
            self._schedule_cleanup()
        return emitted

    async def subscribe(
        self,
        *,
        channels: set[str],
        namespaces: list[list[str]] | None,
        depth: int | None,
        since: int | None,
    ) -> RunSubscription:
        async with self._lock:
            self.had_subscriber = True
            if self._orphan_task is not None:
                self._orphan_task.cancel()
                self._orphan_task = None
            replay = [
                event
                for event in self.events_buffer
                if (since is None or event["seq"] > since)
                and event_matches(
                    event,
                    channels=channels,
                    namespaces=namespaces,
                    depth=depth,
                )
            ]
            subscription = RunSubscription(
                session=self,
                queue=asyncio.Queue(),
                replay=replay,
                channels=channels,
                namespaces=namespaces,
                depth=depth,
            )
            if not self.finished:
                self.subscribers.add(subscription)
            return subscription

    async def unsubscribe(self, subscription: RunSubscription) -> None:
        async with self._lock:
            self.subscribers.discard(subscription)
            should_cancel = self.had_subscriber and self._should_cancel()
            if should_cancel and self._orphan_task is None:
                self._orphan_task = asyncio.create_task(
                    self._cancel_if_still_orphaned(
                        self.registry.disconnect_grace_seconds
                    )
                )

    def arm_initial_subscriber_timeout(self, timeout_seconds: float) -> None:
        if self._orphan_task is None:
            self._orphan_task = asyncio.create_task(
                self._cancel_if_still_orphaned(timeout_seconds)
            )

    def _should_cancel(self) -> bool:
        return (
            not self.finished
            and not self.subscribers
            and self.task is not None
            and not self.task.done()
        )

    async def _cancel_if_still_orphaned(self, delay: float) -> None:
        try:
            await asyncio.sleep(delay)
            async with self._lock:
                should_cancel = self._should_cancel()
            if should_cancel and self.task is not None:
                self.task.cancel()
        except asyncio.CancelledError:
            return
        finally:
            if self._orphan_task is asyncio.current_task():
                self._orphan_task = None

    def _schedule_cleanup(self) -> None:
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_later())

    async def _cleanup_later(self) -> None:
        await asyncio.sleep(self.registry.finished_ttl_seconds)
        await self.registry.remove_if_current(self.conversation_id, self)


HEARTBEAT = _HEARTBEAT
