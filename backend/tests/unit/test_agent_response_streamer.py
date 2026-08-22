from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from app.services.chat.agent_response_streamer import AgentResponseStreamer


def _streamer(publisher=None):
    publisher = publisher or AsyncMock()
    streamer = AgentResponseStreamer(
        publisher,
        conversation_id=uuid4(),
        user_id=uuid4(),
        document_ids=[uuid4()],
        conversation_context=[HumanMessage(content="Question")],
    )
    return streamer, publisher


async def _stream(chunks):
    streamer, publisher = _streamer()

    async def agent_stream(*_args, **_kwargs):
        for chunk in chunks:
            yield chunk

    agent = SimpleNamespace(astream=agent_stream)
    with patch(
        "app.services.chat.agent_response_streamer.get_agent_orchestrator",
        return_value=agent,
    ):
        text = await streamer.stream()
    return text, streamer, publisher


def _model_delta(text: str, *, node: str = "model"):
    return {
        "type": "messages",
        "data": (
            AIMessageChunk(content=text),
            {"langgraph_node": node},
        ),
    }


def _update(node: str, message):
    return {
        "type": "updates",
        "data": {node: {"messages": [message]}},
    }


async def test_stream_appends_model_text_deltas_and_publishes_them():
    text, _streamer_obj, publisher = await _stream(
        [_model_delta("Hel"), _model_delta("lo")]
    )

    assert text == "Hello"
    assert publisher.text_delta.await_args_list[0].args == ("Hel",)
    assert publisher.text_delta.await_args_list[1].args == ("lo",)


async def test_stream_ignores_non_model_nodes_and_malformed_chunks():
    text, _streamer_obj, publisher = await _stream(
        [
            {"type": "messages", "data": "not-a-tuple"},
            {"type": "messages", "data": (AIMessageChunk(content="x"), "meta")},
            _model_delta("kept", node="tools"),
            {"type": "other", "data": {}},
            _model_delta(""),
            _model_delta("OK"),
        ]
    )

    assert text == "OK"
    publisher.text_delta.assert_awaited_once_with("OK")


async def test_stream_uses_completed_ai_message_as_fallback_without_deltas():
    text, _streamer_obj, publisher = await _stream(
        [
            _update(
                "model",
                AIMessage(content="Full answer"),
            )
        ]
    )

    assert text == "Full answer"
    publisher.text_delta.assert_not_awaited()


async def test_stream_raises_when_agent_returns_no_assistant_text():
    with pytest.raises(RuntimeError, match="without an assistant response"):
        await _stream([{"type": "updates", "data": "not-a-dict"}])


async def test_stream_publishes_tool_started_and_finished():
    text, streamer, publisher = await _stream(
        [
            _update(
                "model",
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "tool-1",
                            "name": "search_documents",
                            "args": {},
                        }
                    ],
                ),
            ),
            _model_delta("Answer"),
            _update(
                "tools",
                ToolMessage(content="result", tool_call_id="tool-1"),
            ),
        ]
    )

    assert text == "Answer"
    publisher.tool_started.assert_awaited_once_with(
        "tool-1",
        "search_documents",
    )
    publisher.tool_finished.assert_awaited_once_with("tool-1")
    assert streamer.active_tool_ids == set()


async def test_duplicate_tool_start_and_unknown_tool_finish_are_ignored():
    _text, streamer, publisher = await _stream(
        [
            _model_delta("Answer"),
            _update(
                "model",
                AIMessage(
                    content="",
                    tool_calls=[
                        {"id": "tool-1", "name": "search_documents", "args": {}},
                        {"id": "tool-1", "name": "search_documents", "args": {}},
                        {"id": "", "name": "search_documents", "args": {}},
                        {"id": "tool-2", "name": "", "args": {}},
                    ],
                ),
            ),
            _update(
                "tools",
                ToolMessage(content="late", tool_call_id="unknown"),
            ),
        ]
    )

    publisher.tool_started.assert_awaited_once_with(
        "tool-1",
        "search_documents",
    )
    publisher.tool_finished.assert_not_awaited()
    assert streamer.active_tool_ids == {"tool-1"}


async def test_tool_call_update_does_not_override_streamed_text():
    text, _streamer_obj, _publisher = await _stream(
        [
            _model_delta("Streamed"),
            _update("model", AIMessage(content="Should not replace")),
        ]
    )

    assert text == "Streamed"


async def test_message_text_ignores_non_string_content():
    streamer, _publisher = _streamer()
    message = SimpleNamespace(text=["not", "a", "string"])

    assert streamer._message_text(message) == ""


async def test_stream_passes_conversation_context_and_runtime_ids():
    streamer, _publisher = _streamer()
    captured = {}

    async def agent_stream(payload, **kwargs):
        captured["payload"] = payload
        captured["kwargs"] = kwargs
        yield _model_delta("ok")

    agent = SimpleNamespace(astream=agent_stream)
    with patch(
        "app.services.chat.agent_response_streamer.get_agent_orchestrator",
        return_value=agent,
    ):
        await streamer.stream()

    assert captured["payload"] == {
        "messages": list(streamer._conversation_context)
    }
    assert captured["kwargs"] == {
        "config": {"run_name": "chat"},
        "context": {
            "conversation_id": streamer._conversation_id,
            "user_id": streamer._user_id,
            "document_ids": streamer._document_ids,
        },
        "stream_mode": ["messages", "updates"],
        "version": "v2",
    }
