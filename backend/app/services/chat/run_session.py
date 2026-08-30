from __future__ import annotations

import asyncio
import json
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from app.services.chat.protocol import (
    ProtocolEvent,
    event_matches,
    is_terminal_event,
)

if TYPE_CHECKING:
    from app.services.chat.redis_store import RedisRunStore
    from app.services.chat.run_registry import RunRegistry

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
    subscription_id: str = field(default_factory=lambda: str(uuid4()))
    _feed_task: asyncio.Task[None] | None = None

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
    registry: RunRegistry
    replay_limit: int
    task: asyncio.Task[None] | None = None
    event_store: RedisRunStore | None = None
    remote: bool = False
    events_buffer: deque[ProtocolEvent] = field(init=False)
    subscribers: set[RunSubscription] = field(default_factory=set)
    seq: int = 0
    finished: bool = False
    had_subscriber: bool = False
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _orphan_task: asyncio.Task[None] | None = None
    _cleanup_task: asyncio.Task[None] | None = None
    _control_task: asyncio.Task[None] | None = None

    def __post_init__(self) -> None:
        self.events_buffer = deque(maxlen=self.replay_limit)
        if self.event_store is not None and not self.remote:
            self._control_task = asyncio.create_task(self._listen_control())

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
            store = self.event_store
            if store is not None:
                await store.append_event(
                    self.conversation_id,
                    self.run_id,
                    emitted,
                    finished=terminal,
                )

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
        if self.remote and self.event_store is not None:
            stored = await self.event_store.list_events(self.conversation_id)
            self.events_buffer = deque(stored, maxlen=self.replay_limit)
            if stored:
                self.seq = int(stored[-1]["seq"])
                self.finished = self.finished or is_terminal_event(stored[-1])

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
            last_seq = replay[-1]["seq"] if replay else (since or 0)
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
                if self.remote and self.event_store is not None:
                    subscription._feed_task = asyncio.create_task(
                        self._feed_remote(subscription, last_seq)
                    )

        if self.event_store is not None:
            await self.event_store.add_subscriber(
                self.conversation_id,
                subscription.subscription_id,
            )
            if self.remote:
                await self.event_store.notify_control(
                    self.conversation_id,
                    "joined",
                )
        return subscription

    async def unsubscribe(self, subscription: RunSubscription) -> None:
        if subscription._feed_task is not None:
            subscription._feed_task.cancel()
            subscription._feed_task = None
        remaining_remote = None
        if self.event_store is not None:
            remaining_remote = await self.event_store.remove_subscriber(
                self.conversation_id,
                subscription.subscription_id,
            )
            if remaining_remote == 0:
                await self.event_store.notify_control(
                    self.conversation_id,
                    "orphan",
                )
        async with self._lock:
            self.subscribers.discard(subscription)
            should_cancel = self.had_subscriber and await self._should_cancel()
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

    async def _should_cancel(self) -> bool:
        if (
            self.finished
            or self.subscribers
            or self.task is None
            or self.task.done()
        ):
            return False
        if self.event_store is not None:
            return await self.event_store.subscriber_count(self.conversation_id) == 0
        return True

    async def _cancel_if_still_orphaned(self, delay: float) -> None:
        try:
            await asyncio.sleep(delay)
            async with self._lock:
                should_cancel = await self._should_cancel()
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

    async def _feed_remote(self, subscription: RunSubscription, last_seq: int) -> None:
        assert self.event_store is not None
        pubsub = self.event_store.redis.pubsub()
        await pubsub.subscribe(self.event_store.channel(self.conversation_id))
        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if message is None or message.get("type") != "message":
                    if self.finished:
                        subscription.queue.put_nowait(_STREAM_END)
                        return
                    continue
                data = message.get("data")
                if not isinstance(data, str):
                    continue
                event = json.loads(data)
                seq = event.get("seq")
                if not isinstance(seq, int) or seq <= last_seq:
                    continue
                last_seq = seq
                terminal = is_terminal_event(event)
                if terminal:
                    self.finished = True
                subscription.queue.put_nowait(event)
                if terminal:
                    subscription.queue.put_nowait(_STREAM_END)
                    return
        except asyncio.CancelledError:
            return
        finally:
            await pubsub.unsubscribe()
            await pubsub.aclose()

    async def _listen_control(self) -> None:
        assert self.event_store is not None
        pubsub = self.event_store.redis.pubsub()
        await pubsub.subscribe(self.event_store.control_channel(self.conversation_id))
        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if message is None or message.get("type") != "message":
                    continue
                data = message.get("data")
                if data == "joined" and self._orphan_task is not None:
                    self._orphan_task.cancel()
                    self._orphan_task = None
                elif data == "orphan" and self._orphan_task is None:
                    self._orphan_task = asyncio.create_task(
                        self._cancel_if_still_orphaned(
                            self.registry.disconnect_grace_seconds
                        )
                    )
        except asyncio.CancelledError:
            return
        finally:
            await pubsub.unsubscribe()
            await pubsub.aclose()

    async def close_background(self) -> None:
        tasks = [
            task
            for task in (self._control_task, self._orphan_task, self._cleanup_task)
            if task is not None
        ]
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._control_task = None
        self._orphan_task = None
        self._cleanup_task = None


HEARTBEAT = _HEARTBEAT
