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


async def test_wait_for_session_after_returns_replacement_run():
    registry = InMemoryRunRegistry(subscriber_timeout_seconds=60)
    conversation_id = uuid4()

    async def first_run(session):
        await session.publish(_event("lifecycle", {"event": "completed"}))

    async def second_run(_session):
        return None

    first = await registry.start(conversation_id, "first", first_run)
    if first.task is not None:
        await first.task
    second = await registry.start(conversation_id, "second", second_run)

    found = await registry.wait_for_session_after(
        conversation_id,
        first,
        timeout=1,
    )

    assert found is second
    if second.task is not None:
        await second.task
    await registry.close()


async def test_wait_for_session_after_times_out_when_run_does_not_change():
    registry = InMemoryRunRegistry(subscriber_timeout_seconds=60)
    release = asyncio.Event()

    async def run(_session):
        await release.wait()

    conversation_id = uuid4()
    session = await registry.start(conversation_id, "run", run)

    found = await registry.wait_for_session_after(
        conversation_id,
        session,
        timeout=0.05,
    )

    assert found is None
    release.set()
    if session.task is not None:
        await session.task
    await registry.close()


async def test_wait_for_session_after_wakes_when_new_run_starts():
    registry = InMemoryRunRegistry(subscriber_timeout_seconds=60)
    conversation_id = uuid4()
    first_done = asyncio.Event()

    async def first_run(session):
        await session.publish(_event("lifecycle", {"event": "completed"}))
        first_done.set()

    async def second_run(_session):
        return None

    first = await registry.start(conversation_id, "first", first_run)
    await first_done.wait()
    if first.task is not None:
        await first.task

    waiter = asyncio.create_task(
        registry.wait_for_session_after(conversation_id, first, timeout=1)
    )
    await asyncio.sleep(0)
    second = await registry.start(conversation_id, "second", second_run)
    found = await waiter

    assert found is second
    if second.task is not None:
        await second.task
    await registry.close()


async def test_remove_if_current_leaves_a_newer_session_in_place():
    registry = InMemoryRunRegistry(subscriber_timeout_seconds=60)
    conversation_id = uuid4()

    async def first_run(session):
        await session.publish(_event("lifecycle", {"event": "completed"}))

    async def second_run(_session):
        return None

    first = await registry.start(conversation_id, "first", first_run)
    if first.task is not None:
        await first.task
    second = await registry.start(conversation_id, "second", second_run)

    await registry.remove_if_current(conversation_id, first)

    assert await registry.get(conversation_id) is second
    await registry.remove_if_current(conversation_id, second)
    assert await registry.get(conversation_id) is None
    if second.task is not None:
        await second.task
    await registry.close()


async def test_finished_run_is_removed_after_ttl():
    registry = InMemoryRunRegistry(
        subscriber_timeout_seconds=60,
        finished_ttl_seconds=0.01,
    )
    conversation_id = uuid4()

    async def run(session):
        await session.publish(_event("lifecycle", {"event": "completed"}))

    session = await registry.start(conversation_id, "run", run)
    if session.task is not None:
        await session.task
    await asyncio.sleep(0.05)

    assert await registry.get(conversation_id) is None
    await registry.close()


async def test_close_cancels_active_runs_and_clears_registry():
    registry = InMemoryRunRegistry(subscriber_timeout_seconds=60)
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def run(_session):
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    conversation_id = uuid4()
    session = await registry.start(conversation_id, "run", run)
    await started.wait()
    await registry.close()

    assert cancelled.is_set()
    assert await registry.get(conversation_id) is None
    assert session.task is not None
    assert session.task.done()


async def test_get_returns_none_for_unknown_conversation():
    registry = InMemoryRunRegistry()
    assert await registry.get(uuid4()) is None
    await registry.close()


async def test_subscriber_arriving_in_time_keeps_run_alive():
    registry = InMemoryRunRegistry(subscriber_timeout_seconds=0.05)
    release = asyncio.Event()

    async def run(_session):
        await release.wait()

    session = await registry.start(uuid4(), "run", run)
    await session.subscribe(
        channels={"lifecycle"},
        namespaces=None,
        depth=None,
        since=None,
    )
    await asyncio.sleep(0.1)

    assert session.task is not None
    assert not session.task.done()
    release.set()
    with suppress(asyncio.CancelledError):
        await session.task
    await registry.close()
