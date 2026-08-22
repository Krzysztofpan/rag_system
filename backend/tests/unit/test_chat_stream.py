import asyncio
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from app.services.chat.stream_runner import ChatStreamRunner


class SessionContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *_args):
        return None


def _collecting_session():
    events = []
    session = SimpleNamespace(
        run_id="run-id",
        publish=AsyncMock(side_effect=lambda event: events.append(event)),
    )
    return session, events


def _message_service():
    message_service = AsyncMock()
    message_service.create_message.side_effect = lambda message: message
    return message_service


def _runner_patches(*, agent, message_service, compact):
    stack = ExitStack()
    stack.enter_context(
        patch(
            "app.services.chat.agent_response_streamer.get_agent_orchestrator",
            return_value=agent,
        )
    )
    stack.enter_context(
        patch(
            "app.services.chat.stream_runner.get_session_factory",
            return_value=lambda: SessionContext(),
        )
    )
    stack.enter_context(
        patch(
            "app.services.chat.stream_runner.create_message_service",
            return_value=message_service,
        )
    )
    stack.enter_context(
        patch(
            "app.services.chat.stream_runner.compact_conversation_memory",
            compact,
        )
    )
    return stack


def _make_runner(session, *, conversation_id=None, user_id=None):
    return ChatStreamRunner(
        session,
        conversation_id=conversation_id or uuid4(),
        user_id=user_id or uuid4(),
        document_ids=[],
        conversation_context=[HumanMessage(content="Question")],
    )


async def test_chat_stream_emits_tokens_tools_values_and_persists_final_message():
    conversation_id = uuid4()
    user_id = uuid4()
    events = []
    session = SimpleNamespace(
        run_id="run-id",
        publish=AsyncMock(side_effect=lambda event: events.append(event)),
    )

    async def agent_stream(*_args, **_kwargs):
        yield {
            "type": "messages",
            "data": (
                AIMessageChunk(content="Answer"),
                {"langgraph_node": "model"},
            ),
        }
        yield {
            "type": "updates",
            "data": {
                "model": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "id": "tool-id",
                                    "name": "search_documents",
                                    "args": {},
                                }
                            ],
                        )
                    ]
                }
            },
        }
        yield {
            "type": "updates",
            "data": {
                "tools": {
                    "messages": [
                        ToolMessage(content="result", tool_call_id="tool-id")
                    ]
                }
            },
        }

    agent = SimpleNamespace(astream=agent_stream)
    message_service = _message_service()
    compact = AsyncMock()
    with _runner_patches(
        agent=agent,
        message_service=message_service,
        compact=compact,
    ):
        runner = ChatStreamRunner(
            session,
            conversation_id=conversation_id,
            user_id=user_id,
            document_ids=[],
            conversation_context=[HumanMessage(content="Question")],
        )
        await runner.run()
        await asyncio.sleep(0)

    message_events = [
        event["params"]["data"]
        for event in events
        if event["method"] == "messages"
    ]
    tool_events = [
        event["params"]["data"]
        for event in events
        if event["method"] == "tools"
    ]
    values = next(
        event["params"]["data"] for event in events if event["method"] == "values"
    )

    assert any(
        event.get("delta", {}).get("text") == "Answer"
        for event in message_events
    )
    assert [event["event"] for event in tool_events] == [
        "tool-started",
        "tool-finished",
    ]
    assert values["persistedMessage"]["text"] == "Answer"
    persisted = message_service.create_message.await_args.args[0]
    assert persisted.text == "Answer"
    compact.assert_awaited_once_with(conversation_id, user_id)


async def test_chat_stream_publishes_interrupted_and_reraises_on_cancel():
    session, events = _collecting_session()
    started = asyncio.Event()

    async def agent_stream(*_args, **_kwargs):
        started.set()
        await asyncio.Event().wait()
        yield {}

    with _runner_patches(
        agent=SimpleNamespace(astream=agent_stream),
        message_service=_message_service(),
        compact=AsyncMock(),
    ):
        task = asyncio.create_task(_make_runner(session).run())
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    lifecycle = [
        event["params"]["data"]["event"]
        for event in events
        if event["method"] == "lifecycle"
    ]
    assert lifecycle == ["running", "interrupted"]


async def test_chat_stream_publishes_failed_without_reraising():
    session, events = _collecting_session()
    compact = AsyncMock()

    async def agent_stream(*_args, **_kwargs):
        yield {
            "type": "updates",
            "data": {
                "model": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "id": "tool-id",
                                    "name": "search_documents",
                                    "args": {},
                                }
                            ],
                        )
                    ]
                }
            },
        }
        raise RuntimeError("agent exploded")

    with _runner_patches(
        agent=SimpleNamespace(astream=agent_stream),
        message_service=_message_service(),
        compact=compact,
    ):
        await _make_runner(session).run()

    tool_events = [
        event["params"]["data"]
        for event in events
        if event["method"] == "tools"
    ]
    message_events = [
        event["params"]["data"]
        for event in events
        if event["method"] == "messages"
    ]
    lifecycle = [
        event["params"]["data"]
        for event in events
        if event["method"] == "lifecycle"
    ]

    assert tool_events[-1] == {
        "event": "tool-error",
        "tool_call_id": "tool-id",
        "message": "Tool execution failed",
    }
    assert any(event.get("code") == "agent_failed" for event in message_events)
    assert lifecycle[-1] == {"event": "failed", "error": "agent exploded"}
    compact.assert_not_awaited()


async def test_chat_stream_failed_when_persist_raises():
    session, events = _collecting_session()
    message_service = AsyncMock()
    message_service.create_message.side_effect = RuntimeError("db down")

    async def agent_stream(*_args, **_kwargs):
        yield {
            "type": "messages",
            "data": (
                AIMessageChunk(content="Answer"),
                {"langgraph_node": "model"},
            ),
        }

    with _runner_patches(
        agent=SimpleNamespace(astream=agent_stream),
        message_service=message_service,
        compact=AsyncMock(),
    ):
        await _make_runner(session).run()

    lifecycle = [
        event["params"]["data"]["event"]
        for event in events
        if event["method"] == "lifecycle"
    ]
    assert lifecycle[-1] == "failed"

