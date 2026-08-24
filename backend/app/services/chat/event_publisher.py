import time
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from app.db.models import Message
from app.services.chat.protocol import ProtocolEvent
from app.services.chat.run_session import RunSession
from app.services.security import PROMPT_ATTACK_MESSAGE, PromptAttackError


class ChatStreamPublisher:
    def __init__(self, session: RunSession) -> None:
        self._session = session

    @staticmethod
    def _format_event(method: str, data: dict[str, Any]) -> ProtocolEvent:
        return {
            "method": method,
            "params": {
                "namespace": [],
                "timestamp": int(time.time() * 1000),
                "data": data,
            },
        }

    @staticmethod
    def _format_persisted_message(message: Message) -> dict[str, Any]:
        role = (
            message.role.value
            if hasattr(message.role, "value")
            else str(message.role)
        )
        return {
            "id": str(message.id),
            "conversationId": str(message.conversation_id),
            "text": message.text,
            "role": role,
            "createdAt": message.created_at.isoformat(),
        }

    async def start(self, message_id: UUID, conversation_id: UUID) -> None:
        await self._publish("lifecycle", {"event": "running"})
        await self._publish(
            "messages",
            {
                "event": "message-start",
                "role": "ai",
                "id": str(message_id),
                "metadata": {
                    "run_id": self._session.run_id,
                    "thread_id": str(conversation_id),
                },
            },
        )
        await self._publish(
            "messages",
            {
                "event": "content-block-start",
                "index": 0,
                "content": {"type": "text", "text": ""},
            },
        )

    async def text_delta(self, text: str) -> None:
        await self._publish(
            "messages",
            {
                "event": "content-block-delta",
                "index": 0,
                "delta": {"type": "text-delta", "text": text},
            },
        )

    async def tool_started(self, tool_call_id: str, tool_name: str) -> None:
        await self._publish(
            "tools",
            {
                "event": "tool-started",
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
            },
        )

    async def tool_finished(self, tool_call_id: str) -> None:
        await self._publish(
            "tools",
            {
                "event": "tool-finished",
                "tool_call_id": tool_call_id,
                "output": None,
            },
        )

    async def finish(self, response_text: str, message: Message) -> None:
        await self._publish(
            "messages",
            {
                "event": "content-block-finish",
                "index": 0,
                "content": {"type": "text", "text": response_text},
            },
        )
        await self._publish("messages", {"event": "message-finish"})
        await self._publish(
            "values",
            {"persistedMessage": self._format_persisted_message(message)},
        )
        await self._publish("lifecycle", {"event": "completed"})

    async def interrupted(self) -> None:
        await self._publish("lifecycle", {"event": "interrupted"})

    async def failed(
        self,
        error: Exception,
        active_tool_ids: Iterable[str],
    ) -> None:
        for tool_call_id in active_tool_ids:
            await self._publish(
                "tools",
                {
                    "event": "tool-error",
                    "tool_call_id": tool_call_id,
                    "message": "Tool execution failed",
                },
            )
        if isinstance(error, PromptAttackError):
            await self._publish(
                "messages",
                {
                    "event": "error",
                    "message": PROMPT_ATTACK_MESSAGE,
                    "code": error.code,
                },
            )
        else:
            await self._publish(
                "messages",
                {
                    "event": "error",
                    "message": "Nie udało się wygenerować odpowiedzi",
                    "code": "agent_failed",
                },
            )
        await self._publish(
            "lifecycle",
            {"event": "failed", "error": str(error)},
        )

    async def _publish(self, method: str, data: dict[str, Any]) -> None:
        await self._session.publish(self._format_event(method, data))
