import asyncio
from unittest.mock import patch
from uuid import uuid4

import pytest
from fakeredis import FakeAsyncRedis

from app.services.conversation_events import (
    HEARTBEAT,
    ConversationEventBroker,
    conversation_updated_event,
)


@pytest.fixture
async def redis():
    client = FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()


def _broker(redis, **kwargs) -> ConversationEventBroker:
    return ConversationEventBroker(redis=redis, **kwargs)


async def test_publish_reaches_subscriber_on_another_broker(redis):
    conversation_id = uuid4()
    event = conversation_updated_event(conversation_id, "Contracts", "finance")
    publisher = _broker(redis)
    subscriber_broker = _broker(redis)

    subscription = await subscriber_broker.subscribe(conversation_id)
    stream = subscription.events()
    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0.05)
    await publisher.publish(conversation_id, event)

    assert await asyncio.wait_for(pending, timeout=1) == event
    await stream.aclose()
    await publisher.close()
    await subscriber_broker.close()


async def test_subscribe_replays_title_published_without_subscribers(redis):
    broker = _broker(redis, replay_ttl_seconds=30)
    conversation_id = uuid4()
    event = conversation_updated_event(conversation_id, "Contracts", "finance")

    await broker.publish(conversation_id, event)
    subscription = await broker.subscribe(conversation_id)

    stream = subscription.events()
    assert await anext(stream) == event
    await stream.aclose()
    await broker.close()


async def test_replayed_title_is_not_delivered_to_a_later_subscribe(redis):
    broker = _broker(redis, replay_ttl_seconds=30)
    conversation_id = uuid4()
    event = conversation_updated_event(conversation_id, "Contracts", "finance")

    await broker.publish(conversation_id, event)
    first = await broker.subscribe(conversation_id)
    await first.events().aclose()

    second = await broker.subscribe(conversation_id)
    assert second.queue.empty()
    await broker.close()


async def test_expired_pending_title_is_not_replayed(redis):
    broker = _broker(redis, replay_ttl_seconds=0.01)
    conversation_id = uuid4()
    event = conversation_updated_event(conversation_id, "Stale", "finance")

    await broker.publish(conversation_id, event)
    await asyncio.sleep(0.03)
    subscription = await broker.subscribe(conversation_id)

    assert subscription.queue.empty()
    await broker.close()


async def test_live_publish_is_not_replayed_to_a_later_subscriber(redis):
    broker = _broker(redis, replay_ttl_seconds=30)
    conversation_id = uuid4()
    event = conversation_updated_event(conversation_id, "Live", "finance")

    first = await broker.subscribe(conversation_id)
    stream = first.events()
    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0.05)
    await broker.publish(conversation_id, event)
    assert await asyncio.wait_for(pending, timeout=1) == event
    await stream.aclose()

    second = await broker.subscribe(conversation_id)
    assert second.queue.empty()
    await broker.close()


async def test_unsubscribe_drops_subscriber_before_later_publish(redis):
    broker = _broker(redis)
    conversation_id = uuid4()
    event = conversation_updated_event(conversation_id, "Invoices", "finance")

    subscription = await broker.subscribe(conversation_id)
    await broker.unsubscribe(subscription)
    await broker.publish(conversation_id, event)

    assert subscription.queue.empty()
    await broker.close()


async def test_publish_reaches_only_matching_conversation_subscribers(redis):
    broker = _broker(redis)
    conversation_id = uuid4()
    other_id = uuid4()
    event = conversation_updated_event(conversation_id, "Contracts", "finance")

    matched = await broker.subscribe(conversation_id)
    other = await broker.subscribe(other_id)
    matched_stream = matched.events()
    pending = asyncio.create_task(anext(matched_stream))
    await asyncio.sleep(0.05)
    await broker.publish(conversation_id, event)

    assert await asyncio.wait_for(pending, timeout=1) == event
    await asyncio.sleep(0.1)
    assert other.queue.empty()
    await matched_stream.aclose()
    await broker.unsubscribe(other)
    await broker.close()


async def test_events_yields_queued_title_payload(redis):
    broker = _broker(redis)
    conversation_id = uuid4()
    event = conversation_updated_event(conversation_id, "Payroll", "finance")
    subscription = await broker.subscribe(conversation_id)
    stream = subscription.events()
    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0.05)
    await broker.publish(conversation_id, event)

    assert await asyncio.wait_for(pending, timeout=1) == event
    await stream.aclose()
    await broker.close()


async def test_events_yields_heartbeat_when_idle(redis):
    broker = _broker(redis)
    conversation_id = uuid4()
    subscription = await broker.subscribe(conversation_id)

    def timeout_after_closing_awaitable(awaitable, timeout=None, **_kwargs):
        if asyncio.iscoroutine(awaitable):
            awaitable.close()
        raise TimeoutError

    with patch(
        "app.services.conversation_events.asyncio.wait_for",
        side_effect=timeout_after_closing_awaitable,
    ):
        stream = subscription.events()
        assert await anext(stream) is HEARTBEAT
    await stream.aclose()

    await broker.close()


async def test_close_ends_live_subscribers(redis):
    broker = _broker(redis)
    conversation_id = uuid4()
    subscription = await broker.subscribe(conversation_id)

    async def close_soon():
        await asyncio.sleep(0)
        await broker.close()

    closer = asyncio.create_task(close_soon())
    items = [item async for item in subscription.events()]
    await closer

    assert items == []
