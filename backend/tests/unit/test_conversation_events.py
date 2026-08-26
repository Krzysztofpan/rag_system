import asyncio
from unittest.mock import patch
from uuid import uuid4

from app.services.conversation_events import (
    HEARTBEAT,
    ConversationEventBroker,
    conversation_title_event,
)


async def test_publish_reaches_only_matching_conversation_subscribers():
    broker = ConversationEventBroker()
    conversation_id = uuid4()
    other_id = uuid4()
    event = conversation_title_event(conversation_id, "Contracts")

    matched = await broker.subscribe(conversation_id)
    other = await broker.subscribe(other_id)

    await broker.publish(conversation_id, event)

    assert matched.queue.get_nowait() == event
    assert other.queue.empty()

    await broker.close()


async def test_unsubscribe_drops_subscriber_before_later_publish():
    broker = ConversationEventBroker()
    conversation_id = uuid4()
    event = conversation_title_event(conversation_id, "Invoices")

    subscription = await broker.subscribe(conversation_id)
    await broker.unsubscribe(subscription)
    await broker.publish(conversation_id, event)

    assert subscription.queue.empty()

    await broker.close()


async def test_subscribe_replays_title_published_without_subscribers():
    broker = ConversationEventBroker(replay_ttl_seconds=30)
    conversation_id = uuid4()
    event = conversation_title_event(conversation_id, "Contracts")

    await broker.publish(conversation_id, event)
    subscription = await broker.subscribe(conversation_id)

    stream = subscription.events()
    assert await anext(stream) == event
    await stream.aclose()

    await broker.close()


async def test_replayed_title_is_not_delivered_to_a_later_subscribe():
    broker = ConversationEventBroker(replay_ttl_seconds=30)
    conversation_id = uuid4()
    event = conversation_title_event(conversation_id, "Contracts")

    await broker.publish(conversation_id, event)
    first = await broker.subscribe(conversation_id)
    await first.events().aclose()

    second = await broker.subscribe(conversation_id)
    assert second.queue.empty()

    await broker.close()


async def test_expired_pending_title_is_not_replayed():
    broker = ConversationEventBroker(replay_ttl_seconds=0.01)
    conversation_id = uuid4()
    event = conversation_title_event(conversation_id, "Stale")

    await broker.publish(conversation_id, event)
    await asyncio.sleep(0.02)
    subscription = await broker.subscribe(conversation_id)

    assert subscription.queue.empty()

    await broker.close()


async def test_live_publish_is_not_replayed_to_a_later_subscriber():
    broker = ConversationEventBroker(replay_ttl_seconds=30)
    conversation_id = uuid4()
    event = conversation_title_event(conversation_id, "Live")

    first = await broker.subscribe(conversation_id)
    await broker.publish(conversation_id, event)
    assert first.queue.get_nowait() == event
    await broker.unsubscribe(first)

    second = await broker.subscribe(conversation_id)
    assert second.queue.empty()

    await broker.close()


async def test_events_yields_queued_title_payload():
    broker = ConversationEventBroker()
    conversation_id = uuid4()
    event = conversation_title_event(conversation_id, "Payroll")
    subscription = await broker.subscribe(conversation_id)
    await broker.publish(conversation_id, event)

    stream = subscription.events()
    assert await anext(stream) == event
    await stream.aclose()

    await broker.close()


async def test_events_yields_heartbeat_when_idle():
    broker = ConversationEventBroker()
    conversation_id = uuid4()
    subscription = await broker.subscribe(conversation_id)

    with patch(
        "app.services.conversation_events.asyncio.wait_for",
        side_effect=TimeoutError,
    ):
        stream = subscription.events()
        assert await anext(stream) is HEARTBEAT
        await stream.aclose()

    await broker.close()


async def test_close_ends_live_subscribers():
    broker = ConversationEventBroker()
    conversation_id = uuid4()
    subscription = await broker.subscribe(conversation_id)

    async def close_soon():
        await asyncio.sleep(0)
        await broker.close()

    closer = asyncio.create_task(close_soon())
    items = [item async for item in subscription.events()]
    await closer

    assert items == []
