from typing import Any

ProtocolEvent = dict[str, Any]

_TERMINAL_LIFECYCLE_EVENTS = {"completed", "failed", "interrupted"}
_CHANNEL_BY_METHOD = {
    "values": "values",
    "updates": "updates",
    "messages": "messages",
    "tools": "tools",
    "custom": "custom",
    "lifecycle": "lifecycle",
    "input.requested": "input",
    "checkpoints": "checkpoints",
    "tasks": "tasks",
}


def event_matches(
    event: ProtocolEvent,
    *,
    channels: set[str],
    namespaces: list[list[str]] | None,
    depth: int | None,
) -> bool:
    channel = _CHANNEL_BY_METHOD.get(event.get("method"))
    if channel not in channels:
        return False

    event_namespace = event.get("params", {}).get("namespace", [])
    if not isinstance(event_namespace, list):
        return False
    if not namespaces:
        return True

    for namespace in namespaces:
        if event_namespace[: len(namespace)] != namespace:
            continue
        if depth is None or len(event_namespace) - len(namespace) <= depth:
            return True
    return False


def is_terminal_event(event: ProtocolEvent) -> bool:
    return (
        event.get("method") == "lifecycle"
        and event.get("params", {}).get("data", {}).get("event")
        in _TERMINAL_LIFECYCLE_EVENTS
    )
