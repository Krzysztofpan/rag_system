from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from langchain.agents.middleware import ModelRequest
from langchain_core.messages import HumanMessage, ToolMessage

from app.agent.document_grounding import (
    DocumentGroundingMiddleware,
    should_require_document_tool,
)


def _request(*, document_ids, messages):
    return ModelRequest(
        model=MagicMock(),
        messages=messages,
        runtime=SimpleNamespace(
            context={"document_ids": document_ids},
        ),
    )


def test_requires_document_tool_when_sources_are_selected():
    request = _request(
        document_ids=[uuid4()],
        messages=[HumanMessage(content="Czy mogę korzystać z publicznego Wi-Fi?")],
    )

    assert should_require_document_tool(request) is True


def test_does_not_require_document_tool_without_selected_sources():
    request = _request(
        document_ids=[],
        messages=[HumanMessage(content="Czy mogę korzystać z publicznego Wi-Fi?")],
    )

    assert should_require_document_tool(request) is False


def test_does_not_require_document_tool_after_a_tool_result():
    request = _request(
        document_ids=[uuid4()],
        messages=[
            HumanMessage(content="Czy mogę korzystać z publicznego Wi-Fi?"),
            ToolMessage(content="policy excerpt", tool_call_id="call-1"),
        ],
    )

    assert should_require_document_tool(request) is False


def test_middleware_sets_tool_choice_any_on_first_call_with_sources():
    captured = {}

    def handler(request):
        captured["tool_choice"] = request.tool_choice
        return "ok"

    middleware = DocumentGroundingMiddleware()
    result = middleware.wrap_model_call(
        _request(
            document_ids=[uuid4()],
            messages=[HumanMessage(content="Question")],
        ),
        handler,
    )

    assert result == "ok"
    assert captured["tool_choice"] == "any"


async def test_middleware_leaves_tool_choice_unset_after_tool_result():
    captured = {}

    async def handler(request):
        captured["tool_choice"] = request.tool_choice
        return "ok"

    middleware = DocumentGroundingMiddleware()
    result = await middleware.awrap_model_call(
        _request(
            document_ids=[uuid4()],
            messages=[
                HumanMessage(content="Question"),
                ToolMessage(content="excerpt", tool_call_id="call-1"),
            ],
        ),
        handler,
    )

    assert result == "ok"
    assert captured["tool_choice"] is None
