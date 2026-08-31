import asyncio
import logging
from collections.abc import Sequence
from uuid import UUID, uuid4

from langchain_core.messages import BaseMessage

from app.background_tasks.memory_compaction_background import compact_conversation_memory
from app.container import create_message_service
from app.db.models import Message
from app.db.session import get_session_factory
from app.lib.tracing import conversation_tracing
from app.schemas.message_source import dump_message_sources
from app.services.chat.agent_response_streamer import AgentResponseStreamer
from app.services.chat.event_publisher import ChatStreamPublisher
from app.services.chat.run_session import RunSession

logger = logging.getLogger(__name__)


class ChatStreamRunner:
    def __init__(
        self,
        session: RunSession,
        *,
        conversation_id: UUID,
        user_id: UUID,
        document_ids: list[UUID],
        conversation_context: Sequence[BaseMessage],
        user_query: str,
    ) -> None:
        self._session = session
        self._conversation_id = conversation_id
        self._user_id = user_id
        self._message_id = uuid4()
        self._publisher = ChatStreamPublisher(session)
        self._response_streamer = AgentResponseStreamer(
            self._publisher,
            conversation_id=conversation_id,
            user_id=user_id,
            document_ids=document_ids,
            conversation_context=conversation_context,
            user_query=user_query,
        )

    async def run(self) -> None:
        with conversation_tracing(
            self._conversation_id,
            user_id=self._user_id,
            tags=["chat"],
        ):
            await self._run_traced()

    async def _run_traced(self) -> None:
        try:
            await self._publisher.start(
                self._message_id,
                self._conversation_id,
            )
            response_text = await self._response_streamer.stream()
            assistant_message = await self._persist_assistant_message(response_text)
            await self._publisher.finish(response_text, assistant_message)
            asyncio.create_task(
                compact_conversation_memory(
                    self._conversation_id,
                    self._user_id,
                )
            )
        except asyncio.CancelledError:
            await self._publisher.interrupted()
            raise
        except Exception as exc:
            await self._publisher.failed(
                exc,
                self._response_streamer.active_tool_ids,
            )
            logger.exception(
                "Chat stream failed",
                extra={
                    "conversation_id": str(self._conversation_id),
                    "run_id": self._session.run_id,
                },
            )

    async def _persist_assistant_message(self, response_text: str) -> Message:
        async with get_session_factory()() as database_session:
            message_service = create_message_service(database_session)
            return await message_service.create_message(
                Message(
                    id=self._message_id,
                    conversation_id=self._conversation_id,
                    text=response_text,
                    role="assistant",
                    sources=dump_message_sources(self._response_streamer.sources),
                )
            )
