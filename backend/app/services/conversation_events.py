"""Conversation-level SSE pub/sub.

In-memory is for unit tests and local uvicorn without Redis. Production and
compose pass a Redis client so publishers (API or a later ingest worker) and
subscribers share the same pending replay and live channel.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from redis.asyncio import Redis

_STREAM_END = object()
_HEARTBEAT = object()

ConversationEvent = dict[str, Any]

CONVERSATION_UPDATED_EVENT = "conversation.updated"
HEARTBEAT = _HEARTBEAT
DEFAULT_REPLAY_TTL_SECONDS = 30

_PENDING_KEY = "rag:ce:{conversation_id}:pending"
_SUBS_KEY = "rag:ce:{conversation_id}:subs"
_CHANNEL = "rag:ce:{conversation_id}:ch"


def conversation_updated_event(
    conversation_id: UUID,
    title: str,
    topic: str,
    documents_summary: str | None = None,
) -> ConversationEvent:
    return {
        "event": CONVERSATION_UPDATED_EVENT,
        "conversationId": str(conversation_id),
        "title": title,
        "topic": topic,
        "documentsSummary": documents_summary,
    }


def _pending_key(conversation_id: UUID) -> str:
    return _PENDING_KEY.format(conversation_id=conversation_id)


def _subs_key(conversation_id: UUID) -> str:
    return _SUBS_KEY.format(conversation_id=conversation_id)


def _channel(conversation_id: UUID) -> str:
    return _CHANNEL.format(conversation_id=conversation_id)


@dataclass(eq=False)
class ConversationEventSubscription:
    broker: ConversationEventBroker
    conversation_id: UUID
    queue: asyncio.Queue[ConversationEvent | object]
    subscription_id: str = field(default_factory=lambda: str(uuid4()))
    pubsub: Any = None
    _feed_task: asyncio.Task[None] | None = None

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
    def __init__(
        self,
        *,
        replay_ttl_seconds: float = DEFAULT_REPLAY_TTL_SECONDS,
        redis: Redis | None = None,
    ) -> None:
        self._replay_ttl_seconds = replay_ttl_seconds
        self._redis = redis
        self._subscribers: dict[UUID, set[ConversationEventSubscription]] = {}
        self._pending: dict[UUID, tuple[ConversationEvent, float]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        conversation_id: UUID,
    ) -> ConversationEventSubscription:
        if self._redis is not None:
            return await self._subscribe_redis(conversation_id)
        return await self._subscribe_memory(conversation_id)

    async def unsubscribe(
        self,
        subscription: ConversationEventSubscription,
    ) -> None:
        if self._redis is not None:
            await self._unsubscribe_redis(subscription)
            return
        await self._unsubscribe_memory(subscription)

    async def publish(
        self,
        conversation_id: UUID,
        event: ConversationEvent,
    ) -> None:
        if self._redis is not None:
            await self._publish_redis(conversation_id, event)
            return
        await self._publish_memory(conversation_id, event)

    async def close(self) -> None:
        async with self._lock:
            groups = list(self._subscribers.values())
            self._subscribers.clear()
            self._pending.clear()
        for subscribers in groups:
            for subscription in subscribers:
                await self._stop_subscription(subscription)
                subscription.queue.put_nowait(_STREAM_END)

    async def _subscribe_memory(
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

    async def _unsubscribe_memory(
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

    async def _publish_memory(
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

    async def _subscribe_redis(
        self,
        conversation_id: UUID,
    ) -> ConversationEventSubscription:
        assert self._redis is not None
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(_channel(conversation_id))
        subscription = ConversationEventSubscription(
            broker=self,
            conversation_id=conversation_id,
            queue=asyncio.Queue(),
            pubsub=pubsub,
        )
        await self._redis.sadd(_subs_key(conversation_id), subscription.subscription_id)
        pending = await self._redis.getdel(_pending_key(conversation_id))
        async with self._lock:
            self._subscribers.setdefault(conversation_id, set()).add(subscription)
        if pending is not None:
            subscription.queue.put_nowait(json.loads(pending))
        subscription._feed_task = asyncio.create_task(self._feed_pubsub(subscription))
        return subscription

    async def _feed_pubsub(self, subscription: ConversationEventSubscription) -> None:
        assert subscription.pubsub is not None
        try:
            while True:
                message = await subscription.pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if message is None or message.get("type") != "message":
                    continue
                data = message.get("data")
                if isinstance(data, str):
                    subscription.queue.put_nowait(json.loads(data))
        except asyncio.CancelledError:
            return

    async def _stop_subscription(
        self,
        subscription: ConversationEventSubscription,
    ) -> None:
        if subscription._feed_task is not None:
            subscription._feed_task.cancel()
            try:
                await subscription._feed_task
            except asyncio.CancelledError:
                pass
            subscription._feed_task = None
        if subscription.pubsub is not None:
            await subscription.pubsub.unsubscribe()
            await subscription.pubsub.aclose()
            subscription.pubsub = None

    async def _unsubscribe_redis(
        self,
        subscription: ConversationEventSubscription,
    ) -> None:
        assert self._redis is not None
        await self._redis.srem(
            _subs_key(subscription.conversation_id),
            subscription.subscription_id,
        )
        await self._stop_subscription(subscription)
        async with self._lock:
            subscribers = self._subscribers.get(subscription.conversation_id)
            if subscribers is None:
                return
            subscribers.discard(subscription)
            if not subscribers:
                self._subscribers.pop(subscription.conversation_id, None)

    async def _publish_redis(
        self,
        conversation_id: UUID,
        event: ConversationEvent,
    ) -> None:
        assert self._redis is not None
        payload = json.dumps(event, separators=(",", ":"))
        subscriber_count = await self._redis.scard(_subs_key(conversation_id))
        if subscriber_count:
            await self._redis.delete(_pending_key(conversation_id))
            await self._redis.publish(_channel(conversation_id), payload)
            return
        await self._redis.set(
            _pending_key(conversation_id),
            payload,
            px=max(int(self._replay_ttl_seconds * 1000), 1),
        )
