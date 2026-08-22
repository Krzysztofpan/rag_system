import asyncio
from unittest.mock import patch
from uuid import uuid4

from app.services.chat import run_session as run_session_module
from app.services.chat.protocol import is_terminal_event
from app.services.chat.run_registry import InMemoryRunRegistry
from app.services.chat.run_session import HEARTBEAT, RunSession


def _event(method: str, data: dict, *, namespace=None):
    return {
        "method": method,
        "params": {
            "namespace": [] if namespace is None else namespace,
            "timestamp": 1,
            "data": data,
        },
    }


def _session(**overrides) -> RunSession:
    registry = overrides.pop(
        "registry",
        InMemoryRunRegistry(subscriber_timeout_seconds=60),
    )
    return RunSession(
        conversation_id=overrides.pop("conversation_id", uuid4()),
        run_id=overrides.pop("run_id", "run"),
        registry=registry,
        replay_limit=overrides.pop("replay_limit", 10),
        **overrides,
    )


async def test_publish_assigns_seq_event_id_and_buffers_events():
    session = _session()

    first = await session.publish(_event("messages", {"event": "start"}))
    second = await session.publish(_event("messages", {"event": "delta"}))

    assert first["seq"] == 1
    assert first["type"] == "event"
    assert first["event_id"] == "run:1"
    assert second["seq"] == 2
    assert list(session.events_buffer) == [first, second]
    assert not session.finished


async def test_publish_drops_oldest_events_when_replay_limit_is_reached():
    session = _session(replay_limit=2)

    await session.publish(_event("messages", {"n": 1}))
    await session.publish(_event("messages", {"n": 2}))
    await session.publish(_event("messages", {"n": 3}))

    assert [event["params"]["data"]["n"] for event in session.events_buffer] == [
        2,
        3,
    ]


async def test_terminal_publish_marks_finished_and_ends_subscribers():
    session = _session()
    subscription = await session.subscribe(
        channels={"lifecycle"},
        namespaces=None,
        depth=None,
        since=None,
    )

    emitted = await session.publish(
        _event("lifecycle", {"event": "completed"})
    )

    assert session.finished
    assert is_terminal_event(emitted)
    queued = [subscription.queue.get_nowait(), subscription.queue.get_nowait()]
    assert queued[0]["params"]["data"]["event"] == "completed"
    assert queued[1] is run_session_module._STREAM_END


async def test_subscribe_replays_matching_events_after_since():
    session = _session()
    await session.publish(_event("lifecycle", {"event": "running"}))
    await session.publish(_event("messages", {"event": "delta", "text": "A"}))
    await session.publish(_event("messages", {"event": "delta", "text": "B"}))
    await session.publish(
        _event("messages", {"event": "delta", "text": "nested"}, namespace=["child"])
    )

    subscription = await session.subscribe(
        channels={"messages"},
        namespaces=[[]],
        depth=0,
        since=2,
    )

    assert [event["params"]["data"]["text"] for event in subscription.replay] == [
        "B"
    ]
    assert session.had_subscriber
    assert subscription in session.subscribers


async def test_subscribe_to_finished_run_does_not_keep_live_subscriber():
    session = _session()
    await session.publish(_event("lifecycle", {"event": "failed", "error": "x"}))

    subscription = await session.subscribe(
        channels={"lifecycle"},
        namespaces=None,
        depth=None,
        since=None,
    )

    assert session.finished
    assert subscription not in session.subscribers
    events = [event async for event in subscription.events()]
    assert [event["params"]["data"]["event"] for event in events] == ["failed"]


async def test_live_events_are_filtered_by_channel():
    session = _session()
    subscription = await session.subscribe(
        channels={"tools"},
        namespaces=None,
        depth=None,
        since=None,
    )
    iterator = subscription.events()
    pending = asyncio.create_task(anext(iterator))
    await asyncio.sleep(0)

    await session.publish(_event("messages", {"event": "delta"}))
    await session.publish(
        _event("tools", {"event": "tool-started", "tool_call_id": "t"})
    )

    event = await asyncio.wait_for(pending, timeout=1)
    assert event["method"] == "tools"
    await iterator.aclose()


async def test_subscription_emits_heartbeat_when_queue_is_idle():
    session = _session()
    subscription = await session.subscribe(
        channels={"messages"},
        namespaces=None,
        depth=None,
        since=None,
    )
    iterator = subscription.events()

    with patch(
        "app.services.chat.run_session.asyncio.wait_for",
        side_effect=TimeoutError,
    ):
        item = await anext(iterator)

    assert item is HEARTBEAT
    await iterator.aclose()
    assert subscription not in session.subscribers


async def test_subscribe_cancels_orphan_timeout():
    session = _session()
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
