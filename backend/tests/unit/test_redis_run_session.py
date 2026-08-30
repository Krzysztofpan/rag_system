import asyncio
from contextlib import suppress
from uuid import uuid4

import pytest
from fakeredis import FakeAsyncRedis

from app.services.chat import run_session as run_session_module
from app.services.chat.protocol import is_terminal_event
from app.services.chat.redis_run_registry import RedisRunRegistry
from app.services.chat.redis_store import RedisRunStore
from app.services.chat.run_session import RunSession


@pytest.fixture
async def redis():
    client = FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()


def _event(method: str, data: dict, *, namespace=None):
    return {
        "method": method,
        "params": {
            "namespace": [] if namespace is None else namespace,
            "timestamp": 1,
            "data": data,
        },
    }


def _session(redis, **overrides) -> RunSession:
    replay_limit = overrides.pop("replay_limit", 10)
    store = overrides.pop(
        "event_store",
        RedisRunStore(redis, replay_limit=replay_limit),
    )
    registry = overrides.pop(
        "registry",
        RedisRunRegistry(redis, subscriber_timeout_seconds=60),
    )
    return RunSession(
        conversation_id=overrides.pop("conversation_id", uuid4()),
        run_id=overrides.pop("run_id", "run"),
        registry=registry,
        replay_limit=replay_limit,
        event_store=store,
        **overrides,
    )


async def _wait_until(predicate, *, timeout: float = 2.0) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("condition not met before timeout")


async def test_publish_assigns_seq_and_persists_to_store(redis):
    store = RedisRunStore(redis, replay_limit=10)
    session = _session(redis, event_store=store)
    try:
        first = await session.publish(_event("messages", {"event": "start"}))
        second = await session.publish(_event("messages", {"event": "delta"}))

        assert first["seq"] == 1
        assert first["type"] == "event"
        assert first["event_id"] == "run:1"
        assert second["seq"] == 2
        assert list(session.events_buffer) == [first, second]
        assert not session.finished
        assert await store.list_events(session.conversation_id) == [first, second]
        assert await store.load_meta(session.conversation_id) == {
            "run_id": "run",
            "finished": False,
            "seq": 2,
        }
    finally:
        await session.close_background()
        await session.registry.close()


async def test_publish_drops_oldest_events_in_store_when_replay_limit_is_reached(
    redis,
):
    store = RedisRunStore(redis, replay_limit=2)
    session = _session(redis, replay_limit=2, event_store=store)
    try:
        await session.publish(_event("messages", {"n": 1}))
        await session.publish(_event("messages", {"n": 2}))
        await session.publish(_event("messages", {"n": 3}))

        stored = await store.list_events(session.conversation_id)
        assert [event["params"]["data"]["n"] for event in stored] == [2, 3]
        assert [
            event["params"]["data"]["n"] for event in session.events_buffer
        ] == [2, 3]
    finally:
        await session.close_background()
        await session.registry.close()


async def test_terminal_publish_marks_finished_in_store_and_ends_subscribers(redis):
    store = RedisRunStore(redis, replay_limit=10)
    session = _session(redis, event_store=store)
    try:
        subscription = await session.subscribe(
            channels={"lifecycle"},
            namespaces=None,
            depth=None,
            since=None,
        )
        emitted = await session.publish(_event("lifecycle", {"event": "completed"}))

        assert session.finished
        assert is_terminal_event(emitted)
        assert await store.load_meta(session.conversation_id) == {
            "run_id": "run",
            "finished": True,
            "seq": 1,
        }
        queued = [subscription.queue.get_nowait(), subscription.queue.get_nowait()]
        assert queued[0]["params"]["data"]["event"] == "completed"
        assert queued[1] is run_session_module._STREAM_END
    finally:
        await session.close_background()
        await session.registry.close()


async def test_remote_subscribe_replays_matching_events_after_since(redis):
    owner = RedisRunRegistry(redis, subscriber_timeout_seconds=60)
    reader = RedisRunRegistry(redis, subscriber_timeout_seconds=60)
    published = asyncio.Event()
    release = asyncio.Event()

    async def run(session):
        await session.publish(_event("lifecycle", {"event": "running"}))
        await session.publish(_event("messages", {"event": "delta", "text": "A"}))
        await session.publish(_event("messages", {"event": "delta", "text": "B"}))
        await session.publish(
            _event(
                "messages",
                {"event": "delta", "text": "nested"},
                namespace=["child"],
            )
        )
        published.set()
        await release.wait()

    conversation_id = uuid4()
    session = await owner.start(conversation_id, "run", run)
    await published.wait()

    remote = await reader.get(conversation_id)
    assert remote is not None
    subscription = await remote.subscribe(
        channels={"messages"},
        namespaces=[[]],
        depth=0,
        since=2,
    )

    assert [event["params"]["data"]["text"] for event in subscription.replay] == [
        "B"
    ]
    assert remote.had_subscriber
    assert subscription in remote.subscribers

    release.set()
    if session.task is not None:
        await session.task
    await remote.unsubscribe(subscription)
    await owner.close()
    await reader.close()


async def test_remote_subscribe_to_finished_run_does_not_keep_live_subscriber(redis):
    owner = RedisRunRegistry(redis, subscriber_timeout_seconds=60)
    reader = RedisRunRegistry(redis, subscriber_timeout_seconds=60)

    async def run(session):
        await session.publish(_event("lifecycle", {"event": "failed", "error": "x"}))

    conversation_id = uuid4()
    session = await owner.start(conversation_id, "run", run)
    if session.task is not None:
        await session.task

    remote = await reader.get(conversation_id)
    assert remote is not None
    assert remote.finished
    subscription = await remote.subscribe(
        channels={"lifecycle"},
        namespaces=None,
        depth=None,
        since=None,
    )

    assert subscription not in remote.subscribers
    events = [event async for event in subscription.events()]
    assert [event["params"]["data"]["event"] for event in events] == ["failed"]
    await owner.close()
    await reader.close()


async def test_remote_live_events_are_filtered_by_channel(redis):
    owner = RedisRunRegistry(redis, subscriber_timeout_seconds=60)
    reader = RedisRunRegistry(redis, subscriber_timeout_seconds=60)
    started = asyncio.Event()
    release = asyncio.Event()

    async def run(session):
        started.set()
        await release.wait()
        await session.publish(_event("messages", {"event": "delta"}))
        await session.publish(
            _event("tools", {"event": "tool-started", "tool_call_id": "t"})
        )

    conversation_id = uuid4()
    session = await owner.start(conversation_id, "run", run)
    await started.wait()

    remote = await reader.get(conversation_id)
    assert remote is not None
    subscription = await remote.subscribe(
        channels={"tools"},
        namespaces=None,
        depth=None,
        since=None,
    )
    iterator = subscription.events()
    pending = asyncio.create_task(anext(iterator))
    await asyncio.sleep(0.05)
    release.set()

    event = await asyncio.wait_for(pending, timeout=2)
    assert event["method"] == "tools"
    await iterator.aclose()
    if session.task is not None:
        await session.task
    await owner.close()
    await reader.close()


async def test_owned_subscribe_cancels_orphan_timeout(redis):
    session = _session(redis)
    try:
        session.arm_initial_subscriber_timeout(60)
        orphan = session._orphan_task
        assert orphan is not None

        await session.subscribe(
            channels={"messages"},
            namespaces=None,
            depth=None,
            since=None,
        )
        await asyncio.sleep(0)

        assert orphan.cancelled()
        assert session._orphan_task is None
    finally:
        await session.close_background()
        await session.registry.close()


async def test_remote_subscribe_cancels_owner_orphan_timeout(redis):
    owner = RedisRunRegistry(redis, subscriber_timeout_seconds=60)
    reader = RedisRunRegistry(redis, subscriber_timeout_seconds=60)
    started = asyncio.Event()
    release = asyncio.Event()

    async def run(_session):
        started.set()
        await release.wait()

    conversation_id = uuid4()
    session = await owner.start(conversation_id, "run", run)
    await started.wait()
    assert session._orphan_task is not None

    remote = await reader.get(conversation_id)
    assert remote is not None
    subscription = await remote.subscribe(
        channels={"lifecycle"},
        namespaces=None,
        depth=None,
        since=None,
    )
    await _wait_until(lambda: session._orphan_task is None)

    assert session.task is not None
    assert not session.task.done()
    release.set()
    if session.task is not None:
        with suppress(asyncio.CancelledError):
            await session.task
    await remote.unsubscribe(subscription)
    await owner.close()
    await reader.close()
