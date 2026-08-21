import asyncio
from contextlib import suppress
from uuid import uuid4

import pytest

from app.services.chat.run_registry import InMemoryRunRegistry


def _event(method: str, data: dict):
    return {
        "method": method,
        "params": {
            "namespace": [],
            "timestamp": 1,
            "data": data,
        },
    }


async def test_subscription_replays_matching_events_after_run_start():
    registry = InMemoryRunRegistry(subscriber_timeout_seconds=60)
    published = asyncio.Event()
    release = asyncio.Event()

    async def run(session):
        await session.publish(_event("lifecycle", {"event": "started"}))
        await session.publish(
            _event(
                "messages",
                {"event": "message-start", "role": "ai", "id": "message"},
            )
        )
        published.set()
        await release.wait()

    session = await registry.start(uuid4(), "run", run)
    await published.wait()
    subscription = await session.subscribe(
        channels={"messages"},
        namespaces=None,
        depth=None,
        since=None,
    )

    iterator = subscription.events()
    replayed = await anext(iterator)
    assert replayed["method"] == "messages"
    assert replayed["seq"] == 2

    release.set()
    if session.task is not None:
        await session.task
    await iterator.aclose()
    await registry.close()


async def test_registry_rejects_a_second_active_run():
    registry = InMemoryRunRegistry(subscriber_timeout_seconds=60)
    release = asyncio.Event()

    async def run(_session):
        await release.wait()

    conversation_id = uuid4()
    session = await registry.start(conversation_id, "first", run)

    with pytest.raises(RuntimeError, match="already active"):
        await registry.start(conversation_id, "second", run)

    release.set()
    if session.task is not None:
        await session.task
    await registry.close()


async def test_run_without_subscriber_is_cancelled_after_timeout():
    registry = InMemoryRunRegistry(subscriber_timeout_seconds=0.01)
    cancelled = asyncio.Event()

    async def run(_session):
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    session = await registry.start(uuid4(), "run", run)
    await asyncio.wait_for(cancelled.wait(), timeout=1)

    assert session.task is not None
    with suppress(asyncio.CancelledError):
        await session.task
    await registry.close()


async def test_run_is_cancelled_after_last_subscriber_disconnects():
    registry = InMemoryRunRegistry(
        subscriber_timeout_seconds=60,
        disconnect_grace_seconds=0.01,
    )
    cancelled = asyncio.Event()

    async def run(_session):
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    session = await registry.start(uuid4(), "run", run)
    await session.publish(
        _event(
            "messages",
            {"event": "message-start", "role": "ai", "id": "message"},
        )
    )
    subscription = await session.subscribe(
        channels={"messages"},
        namespaces=None,
        depth=None,
        since=None,
    )
    iterator = subscription.events()
    await anext(iterator)
    await iterator.aclose()

    await asyncio.wait_for(cancelled.wait(), timeout=1)
    assert session.task is not None
    with suppress(asyncio.CancelledError):
        await session.task
    await registry.close()
