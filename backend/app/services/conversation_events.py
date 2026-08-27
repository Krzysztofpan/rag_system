"""In-process pub/sub for conversation-level SSE.

Use one ASGI worker with this implementation. A multi-worker deployment must
replace the broker with shared storage so publishers and subscribers observe
the same events.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from uuid import UUID

_STREAM_END = object()
_HEARTBEAT = object()

ConversationEvent = dict[str, Any]

CONVERSATION_UPDATED_EVENT = "conversation.updated"
HEARTBEAT = _HEARTBEAT
DEFAULT_REPLAY_TTL_SECONDS = 30


def conversation_updated_event(
    conversation_id: UUID,
    title: str,
    topic: str,
) -> ConversationEvent:
    return {
        "event": CONVERSATION_UPDATED_EVENT,
        "conversationId": str(conversation_id),
        "title": title,
        "topic": topic,
    }


@dataclass(eq=False)
class ConversationEventSubscription:
    broker: ConversationEventBroker
    conversation_id: UUID
    queue: asyncio.Queue[ConversationEvent | object]

    async def events(self) -> AsyncIterator[ConversationEvent | object]:
        try:
            while True:
                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout=5)
                except TimeoutError:
                    yield _HEARTBEAT
                    continue
                if item is _STREAM_END:
                    return
                yield item
        finally:
            await self.broker.unsubscribe(self)


class ConversationEventBroker:
    def __init__(self, *, replay_ttl_seconds: float = DEFAULT_REPLAY_TTL_SECONDS) -> None:
        self._replay_ttl_seconds = replay_ttl_seconds
        self._subscribers: dict[UUID, set[ConversationEventSubscription]] = {}
        self._pending: dict[UUID, tuple[ConversationEvent, float]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        conversation_id: UUID,
    ) -> ConversationEventSubscription:
        subscription = ConversationEventSubscription(
            broker=self,
            conversation_id=conversation_id,
            queue=asyncio.Queue(),
        )
        async with self._lock:
            self._subscribers.setdefault(conversation_id, set()).add(subscription)
            pending = self._pending.pop(conversation_id, None)
            if pending is not None:
                event, stored_at = pending
                if time.monotonic() - stored_at <= self._replay_ttl_seconds:
                    subscription.queue.put_nowait(event)
        return subscription

    async def unsubscribe(
        self,
        subscription: ConversationEventSubscription,
    ) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(subscription.conversation_id)
            if subscribers is None:
                return
            subscribers.discard(subscription)
            if not subscribers:
                self._subscribers.pop(subscription.conversation_id, None)

    async def publish(
        self,
        conversation_id: UUID,
        event: ConversationEvent,
    ) -> None:
        async with self._lock:
            subscribers = list(self._subscribers.get(conversation_id, ()))
            if subscribers:
                self._pending.pop(conversation_id, None)
            else:
                self._pending[conversation_id] = (event, time.monotonic())
        for subscription in subscribers:
            subscription.queue.put_nowait(event)

    async def close(self) -> None:
        async with self._lock:
            groups = list(self._subscribers.values())
            self._subscribers.clear()
            self._pending.clear()
        for subscribers in groups:
            for subscription in subscribers:
                subscription.queue.put_nowait(_STREAM_END)
