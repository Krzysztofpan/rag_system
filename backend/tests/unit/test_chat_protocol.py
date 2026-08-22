from app.services.chat.protocol import event_matches, is_terminal_event


def _event(method: str, *, namespace=None, data=None):
    return {
        "method": method,
        "params": {
            "namespace": [] if namespace is None else namespace,
            "timestamp": 1,
            "data": {} if data is None else data,
        },
    }


def test_event_matches_unknown_method():
    assert not event_matches(
        _event("unknown"),
        channels={"messages"},
        namespaces=None,
        depth=None,
    )


def test_event_matches_channel_not_requested():
    assert not event_matches(
        _event("tools"),
        channels={"messages", "lifecycle"},
        namespaces=None,
        depth=None,
    )


def test_event_matches_maps_input_requested_to_input_channel():
    assert event_matches(
        _event("input.requested"),
        channels={"input"},
        namespaces=None,
        depth=None,
    )


def test_event_matches_rejects_non_list_namespace():
    assert not event_matches(
        _event("messages", namespace="agent"),
        channels={"messages"},
        namespaces=None,
        depth=None,
    )


def test_event_matches_all_namespaces_when_filter_is_empty():
    event = _event("messages", namespace=["agent", "child"])

    assert event_matches(
        event,
        channels={"messages"},
        namespaces=None,
        depth=0,
    )
    assert event_matches(
        event,
        channels={"messages"},
        namespaces=[],
        depth=0,
    )


def test_event_matches_namespace_prefix_and_depth():
    event = _event("updates", namespace=["agent", "child"])

    assert event_matches(
        event,
        channels={"updates"},
        namespaces=[["agent"]],
        depth=None,
    )
    assert event_matches(
        event,
        channels={"updates"},
        namespaces=[["agent"]],
        depth=1,
    )
    assert not event_matches(
        event,
        channels={"updates"},
        namespaces=[["agent"]],
        depth=0,
    )
    assert event_matches(
        event,
        channels={"updates"},
        namespaces=[["agent", "child"]],
        depth=0,
    )


def test_event_matches_rejects_unrelated_namespace():
    assert not event_matches(
        _event("custom", namespace=["agent"]),
        channels={"custom"},
        namespaces=[["other"]],
        depth=None,
    )


def test_is_terminal_event_for_completed_failed_and_interrupted():
    for event_name in ("completed", "failed", "interrupted"):
        assert is_terminal_event(
            _event("lifecycle", data={"event": event_name})
        )


def test_is_terminal_event_rejects_running_and_non_lifecycle():
    assert not is_terminal_event(_event("lifecycle", data={"event": "running"}))
    assert not is_terminal_event(
        _event("messages", data={"event": "completed"})
    )
    assert not is_terminal_event({"method": "lifecycle"})
