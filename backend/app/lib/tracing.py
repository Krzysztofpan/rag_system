from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from langsmith import trace as langsmith_trace, tracing_context

THREAD_ID_KEY = "thread_id"


def conversation_metadata(
    conversation_id: UUID,
    *,
    user_id: UUID | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    metadata = {
        THREAD_ID_KEY: str(conversation_id),
        "conversation_id": str(conversation_id),
    }
    if user_id is not None:
        metadata["user_id"] = str(user_id)
    if extra:
        metadata.update({key: str(value) for key, value in extra.items()})
    return metadata


def _trace_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def traced_run(
    name: str,
    *,
    run_type: str = "chain",
    inputs: Mapping[str, Any] | None = None,
):
    """Open a LangSmith span. `conversation_tracing` only attaches metadata."""
    serialized = (
        {key: _trace_value(value) for key, value in inputs.items()}
        if inputs
        else None
    )
    return langsmith_trace(name, run_type=run_type, inputs=serialized)


@contextmanager
def conversation_tracing(
    conversation_id: UUID,
    *,
    user_id: UUID | None = None,
    tags: list[str] | None = None,
    extra_metadata: Mapping[str, Any] | None = None,
    as_root: bool = False,
) -> Iterator[None]:
    """Attach conversation thread metadata to every LangSmith run in this scope.

    `as_root=True` starts a new trace (needed so a nested LangGraph keeps
    the node waterfall instead of inheriting the agent parent).
    """
    with tracing_context(
        parent=False if as_root else None,
        tags=list(tags or []),
        metadata=conversation_metadata(
            conversation_id,
            user_id=user_id,
            extra=extra_metadata,
        ),
    ):
        yield
