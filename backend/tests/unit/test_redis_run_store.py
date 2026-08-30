from uuid import uuid4

import pytest
from fakeredis import FakeAsyncRedis

from app.services.chat.redis_store import RedisRunStore


@pytest.fixture
async def redis():
    client = FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()


def _store(redis, replay_limit: int = 10) -> RedisRunStore:
    return RedisRunStore(redis, replay_limit=replay_limit)


def _event(method: str, data: dict, seq: int):
    return {
        "type": "event",
        "event_id": f"run:{seq}",
        "seq": seq,
        "method": method,
        "params": {
            "namespace": [],
            "timestamp": 1,
            "data": data,
        },
    }


async def test_try_acquire_writes_unfinished_meta(redis):
    store = _store(redis)
    conversation_id = uuid4()

    assert await store.try_acquire(conversation_id, "run") is True
    assert await store.load_meta(conversation_id) == {
        "run_id": "run",
        "finished": False,
        "seq": 0,
    }


async def test_try_acquire_rejects_an_active_run(redis):
    store = _store(redis)
    conversation_id = uuid4()

    assert await store.try_acquire(conversation_id, "first") is True
    assert await store.try_acquire(conversation_id, "second") is False
    assert (await store.load_meta(conversation_id))["run_id"] == "first"


async def test_try_acquire_replaces_finished_run_and_clears_events(redis):
    store = _store(redis)
    conversation_id = uuid4()

    assert await store.try_acquire(conversation_id, "first") is True
    await store.append_event(
        conversation_id,
        "first",
        _event("lifecycle", {"event": "completed"}, 1),
        finished=True,
    )
    await store.add_subscriber(conversation_id, "stale")

    assert await store.try_acquire(conversation_id, "second") is True
    assert await store.load_meta(conversation_id) == {
        "run_id": "second",
        "finished": False,
        "seq": 0,
    }
    assert await store.list_events(conversation_id) == []
    assert await store.subscriber_count(conversation_id) == 0


async def test_append_event_persists_events_and_meta(redis):
    store = _store(redis)
    conversation_id = uuid4()
    first = _event("messages", {"event": "start"}, 1)
    second = _event("messages", {"event": "delta"}, 2)

    await store.append_event(conversation_id, "run", first, finished=False)
    await store.append_event(conversation_id, "run", second, finished=False)

    assert await store.list_events(conversation_id) == [first, second]
    assert await store.load_meta(conversation_id) == {
        "run_id": "run",
        "finished": False,
        "seq": 2,
    }


async def test_append_event_trims_to_replay_limit(redis):
    store = _store(redis, replay_limit=2)
    conversation_id = uuid4()

    for seq in (1, 2, 3):
        await store.append_event(
            conversation_id,
            "run",
            _event("messages", {"n": seq}, seq),
            finished=False,
        )

    stored = await store.list_events(conversation_id)
    assert [event["params"]["data"]["n"] for event in stored] == [2, 3]


async def test_subscriber_count_tracks_add_and_remove(redis):
    store = _store(redis)
    conversation_id = uuid4()

    await store.add_subscriber(conversation_id, "a")
    await store.add_subscriber(conversation_id, "b")
    assert await store.subscriber_count(conversation_id) == 2

    assert await store.remove_subscriber(conversation_id, "a") == 1
    assert await store.remove_subscriber(conversation_id, "b") == 0
    assert await store.subscriber_count(conversation_id) == 0


async def test_delete_if_run_removes_matching_keys_only(redis):
    store = _store(redis)
    conversation_id = uuid4()
    await store.try_acquire(conversation_id, "run")
    await store.append_event(
        conversation_id,
        "run",
        _event("messages", {"event": "start"}, 1),
        finished=False,
    )
    await store.add_subscriber(conversation_id, "sub")

    await store.delete_if_run(conversation_id, "other")
    assert await store.load_meta(conversation_id) is not None
    assert await store.list_events(conversation_id)
    assert await store.subscriber_count(conversation_id) == 1

    await store.delete_if_run(conversation_id, "run")
    assert await store.load_meta(conversation_id) is None
    assert await store.list_events(conversation_id) == []
    assert await store.subscriber_count(conversation_id) == 0


async def test_load_meta_returns_none_when_missing(redis):
    store = _store(redis)
    assert await store.load_meta(uuid4()) is None
