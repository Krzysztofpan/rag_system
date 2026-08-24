from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.db.models import Message, MessageRole
from app.services.chat.event_publisher import ChatStreamPublisher
from app.services.security import PROMPT_ATTACK_MESSAGE, PromptAttackError


def _publisher():
    session = SimpleNamespace(run_id="run-id", publish=AsyncMock())
    session.publish.side_effect = lambda event: event
    return ChatStreamPublisher(session), session


def _payloads(session):
    return [
        (call.args[0]["method"], call.args[0]["params"]["data"])
        for call in session.publish.await_args_list
    ]


def _message(*, role=MessageRole.assistant):
    conversation_id = uuid4()
    return Message(
        id=uuid4(),
        conversation_id=conversation_id,
        text="Final answer",
        role=role,
        created_at=datetime(2026, 8, 22, 12, 0, tzinfo=UTC),
    )


async def test_start_emits_running_and_message_block_openers():
    publisher, session = _publisher()
    message_id = uuid4()
    conversation_id = uuid4()

    await publisher.start(message_id, conversation_id)

    assert _payloads(session) == [
        ("lifecycle", {"event": "running"}),
        (
            "messages",
            {
                "event": "message-start",
                "role": "ai",
                "id": str(message_id),
                "metadata": {
                    "run_id": "run-id",
                    "thread_id": str(conversation_id),
                },
            },
        ),
        (
            "messages",
            {
                "event": "content-block-start",
                "index": 0,
                "content": {"type": "text", "text": ""},
            },
        ),
    ]
    for event in session.publish.await_args_list:
        params = event.args[0]["params"]
        assert params["namespace"] == []
        assert isinstance(params["timestamp"], int)


async def test_text_and_tool_events():
    publisher, session = _publisher()

    await publisher.text_delta("Hello")
    await publisher.tool_started("tool-1", "search_documents")
    await publisher.tool_finished("tool-1")

    assert _payloads(session) == [
        (
            "messages",
            {
                "event": "content-block-delta",
                "index": 0,
                "delta": {"type": "text-delta", "text": "Hello"},
            },
        ),
        (
            "tools",
            {
                "event": "tool-started",
                "tool_call_id": "tool-1",
                "tool_name": "search_documents",
            },
        ),
        (
            "tools",
            {
                "event": "tool-finished",
                "tool_call_id": "tool-1",
                "output": None,
            },
        ),
    ]


async def test_finish_emits_message_close_persisted_value_and_completed():
    publisher, session = _publisher()
    message = _message()

    await publisher.finish("Final answer", message)

    assert _payloads(session) == [
        (
            "messages",
            {
                "event": "content-block-finish",
                "index": 0,
                "content": {"type": "text", "text": "Final answer"},
            },
        ),
        ("messages", {"event": "message-finish"}),
        (
            "values",
            {
                "persistedMessage": {
                    "id": str(message.id),
                    "conversationId": str(message.conversation_id),
                    "text": "Final answer",
                    "role": "assistant",
                    "createdAt": message.created_at.isoformat(),
                }
            },
        ),
        ("lifecycle", {"event": "completed"}),
    ]


async def test_format_persisted_message_accepts_string_role():
    publisher, _session = _publisher()
    message = SimpleNamespace(
        id=uuid4(),
        conversation_id=uuid4(),
        text="Hi",
        role="user",
        created_at=datetime(2026, 8, 22, tzinfo=UTC),
    )

    formatted = publisher._format_persisted_message(message)

    assert formatted["role"] == "user"


async def test_interrupted_emits_lifecycle_event():
    publisher, session = _publisher()

    await publisher.interrupted()

    assert _payloads(session) == [("lifecycle", {"event": "interrupted"})]


async def test_failed_closes_active_tools_and_emits_error():
    publisher, session = _publisher()

    await publisher.failed(RuntimeError("boom"), ["tool-1", "tool-2"])

    assert _payloads(session) == [
        (
            "tools",
            {
                "event": "tool-error",
                "tool_call_id": "tool-1",
                "message": "Tool execution failed",
            },
        ),
        (
            "tools",
            {
                "event": "tool-error",
                "tool_call_id": "tool-2",
                "message": "Tool execution failed",
            },
        ),
        (
            "messages",
            {
                "event": "error",
                "message": "Nie udało się wygenerować odpowiedzi",
                "code": "agent_failed",
            },
        ),
        ("lifecycle", {"event": "failed", "error": "boom"}),
    ]


async def test_failed_without_active_tools_skips_tool_errors():
    publisher, session = _publisher()

    await publisher.failed(ValueError("no tools"), [])

    methods = [method for method, _data in _payloads(session)]
    assert methods == ["messages", "lifecycle"]


async def test_failed_emits_prompt_attack_code():
    publisher, session = _publisher()

    await publisher.failed(PromptAttackError(), [])

    assert _payloads(session) == [
        (
            "messages",
            {
                "event": "error",
                "message": PROMPT_ATTACK_MESSAGE,
                "code": "prompt_attack",
            },
        ),
        ("lifecycle", {"event": "failed", "error": PROMPT_ATTACK_MESSAGE}),
    ]
