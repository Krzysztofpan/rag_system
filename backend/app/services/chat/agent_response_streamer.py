from collections.abc import Sequence
from typing import Any
from uuid import UUID

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolMessage

from app.agent.agent_orchestrator import get_agent_orchestrator
from app.services.chat.event_publisher import ChatStreamPublisher


class AgentResponseStreamer:
    def __init__(
        self,
        publisher: ChatStreamPublisher,
        *,
        conversation_id: UUID,
        user_id: UUID,
        document_ids: list[UUID],
        conversation_context: Sequence[BaseMessage],
        user_query: str,
    ) -> None:
        self._publisher = publisher
        self._conversation_id = conversation_id
        self._user_id = user_id
        self._document_ids = document_ids
        self._conversation_context = conversation_context
        self._user_query = user_query

        self._response_parts: list[str] = []
        self._fallback_response = ""
        self._active_tools: set[str] = set()

    @property
    def active_tool_ids(self) -> set[str]:
        return self._active_tools.copy()

    @property
    def _response_text(self) -> str:
        return "".join(self._response_parts) or self._fallback_response

    async def stream(self) -> str:
        agent = get_agent_orchestrator()
        async for chunk in agent.astream(
            {"messages": list(self._conversation_context)},
            config={"run_name": "chat"},
            context={
                "conversation_id": self._conversation_id,
                "user_id": self._user_id,
                "document_ids": self._document_ids,
                "user_query": self._user_query,
            },
            stream_mode=["messages", "updates"],
            version="v2",
        ):
            await self._handle_chunk(chunk)

        response_text = self._response_text
        if not response_text:
            raise RuntimeError("Agent completed without an assistant response")
        return response_text

    async def _handle_chunk(self, chunk: dict[str, Any]) -> None:
        chunk_type = chunk.get("type")
        data = chunk.get("data")
        if chunk_type == "messages":
            await self._handle_message_chunk(data)
        elif chunk_type == "updates":
            await self._handle_updates(data)

    async def _handle_message_chunk(self, data: Any) -> None:
        if not isinstance(data, tuple) or len(data) != 2:
            return

        message_chunk, metadata = data
        if (
            not isinstance(message_chunk, AIMessageChunk)
            or not isinstance(metadata, dict)
            or metadata.get("langgraph_node") != "model"
        ):
            return

        text = self._message_text(message_chunk)
        if not text:
            return

        self._response_parts.append(text)
        await self._publisher.text_delta(text)

    async def _handle_updates(self, data: Any) -> None:
        if not isinstance(data, dict):
            return

        for update in data.values():
            messages = update.get("messages") if isinstance(update, dict) else None
            if not messages:
                continue
            await self._handle_completed_message(messages[-1])

    async def _handle_completed_message(self, completed: BaseMessage) -> None:
        if isinstance(completed, AIMessage):
            await self._handle_ai_message(completed)
        elif isinstance(completed, ToolMessage):
            await self._handle_tool_message(completed)

    async def _handle_ai_message(self, message: AIMessage) -> None:
        completed_text = self._message_text(message)
        if completed_text and not message.tool_calls:
            self._fallback_response = completed_text

        for tool_call in message.tool_calls:
            tool_call_id = tool_call.get("id")
            tool_name = tool_call.get("name")
            if (
                not tool_call_id
                or not tool_name
                or tool_call_id in self._active_tools
            ):
                continue
            self._active_tools.add(tool_call_id)
            await self._publisher.tool_started(tool_call_id, tool_name)

    async def _handle_tool_message(self, message: ToolMessage) -> None:
        tool_call_id = message.tool_call_id
        if tool_call_id not in self._active_tools:
            return

        self._active_tools.remove(tool_call_id)
        await self._publisher.tool_finished(tool_call_id)

    @staticmethod
    def _message_text(message: AIMessage | AIMessageChunk) -> str:
        text = message.text
        return text if isinstance(text, str) else ""
