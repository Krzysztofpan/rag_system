from collections.abc import Awaitable, Callable, Sequence
from typing import Any
from uuid import UUID

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from app.agent.types import AgentContext

ModelCallResult = ModelResponse[Any] | AIMessage


def selected_document_ids(request: ModelRequest[AgentContext]) -> list[UUID]:
    context = getattr(request.runtime, "context", None)
    if not context:
        return []
    return list(context.get("document_ids") or [])


def has_tool_result(messages: Sequence[BaseMessage]) -> bool:
    return any(isinstance(message, ToolMessage) for message in messages)


def should_require_document_tool(request: ModelRequest[AgentContext]) -> bool:
    return bool(selected_document_ids(request)) and not has_tool_result(
        request.messages
    )


class DocumentGroundingMiddleware(AgentMiddleware[Any, AgentContext]):
    """Force a document tool on the first model call when sources are selected."""

    def _prepare(
        self,
        request: ModelRequest[AgentContext],
    ) -> ModelRequest[AgentContext]:
        if should_require_document_tool(request):
            return request.override(tool_choice="any")
        return request

    def wrap_model_call(
        self,
        request: ModelRequest[AgentContext],
        handler: Callable[[ModelRequest[AgentContext]], ModelResponse[Any]],
    ) -> ModelCallResult:
        return handler(self._prepare(request))

    async def awrap_model_call(
        self,
        request: ModelRequest[AgentContext],
        handler: Callable[
            [ModelRequest[AgentContext]],
            Awaitable[ModelResponse[Any]],
        ],
    ) -> ModelCallResult:
        return await handler(self._prepare(request))
