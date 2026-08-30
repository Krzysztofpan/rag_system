import asyncio
from uuid import uuid4

import pytest
from fakeredis import FakeAsyncRedis

from app.services.chat.redis_run_registry import RedisRunRegistry


def _event(method: str, data: dict):
    return {
        "method": method,
        "params": {
            "namespace": [],
            "timestamp": 1,
            "data": data,
        },
    }


@pytest.fixture
async def redis():
    client = FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()


def _registry(redis, **kwargs) -> RedisRunRegistry:
    return RedisRunRegistry(redis, **kwargs)


async def test_second_registry_rejects_active_run(redis):
    owner = _registry(redis, subscriber_timeout_seconds=60)
    other = _registry(redis, subscriber_timeout_seconds=60)
    release = asyncio.Event()

    async def run(_session):
        await release.wait()

    conversation_id = uuid4()
    session = await owner.start(conversation_id, "first", run)

    with pytest.raises(RuntimeError, match="already active"):
        await other.start(conversation_id, "second", run)

    release.set()
    if session.task is not None:
        await session.task
    await owner.close()
    await other.close()


async def test_remote_subscribe_replays_events(redis):
    owner = _registry(redis, subscriber_timeout_seconds=60)
    reader = _registry(redis, subscriber_timeout_seconds=60)
    published = asyncio.Event()
    release = asyncio.Event()

    async def run(session):
        await session.publish(_event("lifecycle", {"event": "started"}))
        await session.publish(
            _event("messages", {"event": "message-start", "role": "ai", "id": "m"})
        )
        published.set()
        await release.wait()

    conversation_id = uuid4()
    session = await owner.start(conversation_id, "run", run)
    await published.wait()

    remote = await reader.get(conversation_id)
    assert remote is not None
    assert remote.run_id == "run"
    subscription = await remote.subscribe(
        channels={"messages"},
        namespaces=None,
        depth=None,
        since=None,
    )
    replayed = await anext(subscription.events())
    assert replayed["method"] == "messages"
    assert replayed["seq"] == 2

    release.set()
    if session.task is not None:
        await session.task
    await subscription.events().aclose()
    await owner.close()
    await reader.close()


async def test_remote_subscribe_receives_live_events(redis):
    owner = _registry(redis, subscriber_timeout_seconds=60)
    reader = _registry(redis, subscriber_timeout_seconds=60)
    started = asyncio.Event()
    release = asyncio.Event()

    async def run(session):
        started.set()
        await release.wait()
        await session.publish(
            _event("messages", {"event": "delta", "text": "hello"})
        )

    conversation_id = uuid4()
    session = await owner.start(conversation_id, "run", run)
    await started.wait()

    remote = await reader.get(conversation_id)
    assert remote is not None
    subscription = await remote.subscribe(
        channels={"messages"},
        namespaces=None,
        depth=None,
        since=None,
    )
    iterator = subscription.events()
    pending = asyncio.create_task(anext(iterator))
    await asyncio.sleep(0.05)
    release.set()

    event = await asyncio.wait_for(pending, timeout=1)
    assert event["params"]["data"]["text"] == "hello"
    await iterator.aclose()
    if session.task is not None:
        await session.task
    await owner.close()
    await reader.close()


async def test_wait_for_session_after_sees_run_started_on_other_registry(redis):
    owner = _registry(redis, subscriber_timeout_seconds=60)
    waiter_registry = _registry(redis, subscriber_timeout_seconds=60)
    conversation_id = uuid4()

    async def first_run(session):
        await session.publish(_event("lifecycle", {"event": "completed"}))

    async def second_run(_session):
        return None

    first = await owner.start(conversation_id, "first", first_run)
    if first.task is not None:
        await first.task

    waiter = asyncio.create_task(
        waiter_registry.wait_for_session_after(conversation_id, first, timeout=1)
    )
    await asyncio.sleep(0.05)
    second = await owner.start(conversation_id, "second", second_run)
    found = await waiter

    assert found is not None
    assert found.run_id == second.run_id
    if second.task is not None:
        await second.task
    await owner.close()
    await waiter_registry.close()


async def test_finished_run_allows_a_new_start(redis):
    registry = _registry(redis, subscriber_timeout_seconds=60)
    conversation_id = uuid4()

    async def first_run(session):
        await session.publish(_event("lifecycle", {"event": "completed"}))

    async def second_run(_session):
        return None

    first = await registry.start(conversation_id, "first", first_run)
    if first.task is not None:
        await first.task
    second = await registry.start(conversation_id, "second", second_run)
    assert second.run_id == "second"
    if second.task is not None:
        await second.task
    await registry.close()


async def test_close_cancels_owned_run(redis):
    registry = _registry(redis, subscriber_timeout_seconds=60)
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
    assert session.task is not None
    assert session.task.done()


async def test_get_returns_none_for_unknown_conversation(redis):
    registry = _registry(redis)
    assert await registry.get(uuid4()) is None
    await registry.close()
