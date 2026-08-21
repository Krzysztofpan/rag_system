import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from app.services.chat.stream_runner import ChatStreamRunner


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
    message_service = AsyncMock()
    message_service.create_message.side_effect = lambda message: message

    class SessionContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *_args):
            return None

    compact = AsyncMock()
    with (
        patch(
            "app.services.chat.agent_response_streamer.get_agent_orchestrator",
            return_value=agent,
        ),
        patch(
            "app.services.chat.stream_runner.get_session_factory",
            return_value=lambda: SessionContext(),
        ),
        patch(
            "app.services.chat.stream_runner.create_message_service",
            return_value=message_service,
        ),
        patch(
            "app.services.chat.stream_runner.compact_conversation_memory",
            compact,
        ),
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
