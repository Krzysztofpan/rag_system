import logging
from datetime import UTC, datetime
from uuid import UUID

import tiktoken
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models.conversation import Conversation
from app.db.models.conversation_summary import ConversationSummary
from app.db.models.message import Message, MessageRole
from app.prompts import (
    conversation_documents_catalog_message,
    conversation_memory_system_message,
)
from app.schemas.conversation_memory import ConversationMemorySummary
from app.services.conversation_memory_compactor import (
    ConversationMemoryCompactor,
    MemoryTurn,
)
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService

logger = logging.getLogger(__name__)


class ConversationMemoryService:
    def __init__(
        self,
        session: AsyncSession,
        conversation_service: ConversationService,
        message_service: MessageService | None = None,
        settings: Settings | None = None,
        compactor: ConversationMemoryCompactor | None = None,
    ):
        self.session = session
        self.conversation_service = conversation_service
        self.message_service = message_service or MessageService(session)
        self.settings = settings or get_settings()
        self.compactor = compactor or ConversationMemoryCompactor(self.settings)

    async def build_context_for_agent(
        self,
        conversation: Conversation,
        *,
        documents_catalog: str | None = None,
    ) -> list[BaseMessage]:
        conversation_id = conversation.id
        user_id = conversation.user_id
        summary_state = await self._get_summary_state(conversation_id)
        message_limit = (
            self.settings.memory_compaction_max_messages
            if self.settings.memory_enabled
            else 1
        )
        messages = await self.message_service.get_messages_after(
            conversation_id,
            user_id=user_id,
            after_id=(
                summary_state.compacted_through_message_id
                if self.settings.memory_enabled and summary_state is not None
                else None
            ),
            limit=message_limit,
            newest_first=True,
        )

        conversation_context: list[BaseMessage] = []
        if documents_catalog:
            conversation_context.append(
                SystemMessage(
                    content=conversation_documents_catalog_message(documents_catalog)
                )
            )
        summary = (
            self._parse_summary(summary_state.messages_summary)
            if self.settings.memory_enabled and summary_state is not None
            else None
        )
        if summary is not None:
            conversation_context.append(
                SystemMessage(
                    content=conversation_memory_system_message(
                        summary.model_dump_json()
                    )
                )
            )

        conversation_context.extend(self._to_langchain_message(message) for message in messages)
        return conversation_context

    async def compact_if_needed(
        self,
        conversation_id: UUID,
        *,
        user_id: UUID,
    ) -> bool:
        if not self.settings.memory_enabled:
            return False

        await self.conversation_service.get_conversation(
            conversation_id,
            user_id=user_id,
        )
        summary_state = await self._get_summary_state(conversation_id)
        old_version = summary_state.version if summary_state is not None else 0
        old_watermark = (
            summary_state.compacted_through_message_id
            if summary_state is not None
            else None
        )
        existing_summary = self._parse_summary(
            summary_state.messages_summary if summary_state is not None else None
        )
        messages = await self.message_service.get_messages_after(
            conversation_id,
            user_id=user_id,
            after_id=old_watermark,
            limit=self.settings.memory_compaction_max_messages,
        )

        token_count = self._count_tokens(messages)
        should_compact = (
            len(messages) >= self.settings.memory_compaction_max_messages
            or token_count >= self.settings.memory_compaction_max_tokens
        )
        keep_count = min(
            self.settings.memory_keep_recent_messages,
            max(len(messages) - 1, 0),
        )
        batch_end = len(messages) - keep_count
        if not should_compact or batch_end <= 0:
            return False

        turns = [
            MemoryTurn(role=message.role, text=message.text)
            for message in messages[:batch_end]
        ]
        new_watermark = messages[batch_end - 1].id

        # End the read transaction before the external LLM call.
        await self.session.rollback()
        new_summary = await self.compactor.merge(existing_summary, turns)

        values = {
            "messages_summary": new_summary.model_dump(mode="json"),
            "compacted_through_message_id": new_watermark,
            "version": old_version + 1,
            "updated_at": datetime.now(UTC),
        }
        if summary_state is None:
            statement = (
                insert(ConversationSummary)
                .values(conversation_id=conversation_id, **values)
                .on_conflict_do_update(
                    index_elements=[ConversationSummary.conversation_id],
                    set_=values,
                    where=(
                        ConversationSummary.compacted_through_message_id.is_(None)
                        & (ConversationSummary.version == 0)
                    ),
                )
            )
        else:
            conditions = [
                ConversationSummary.conversation_id == conversation_id,
                ConversationSummary.version == old_version,
            ]
            if old_watermark is None:
                conditions.append(
                    ConversationSummary.compacted_through_message_id.is_(None)
                )
            else:
                conditions.append(
                    ConversationSummary.compacted_through_message_id
                    == old_watermark
                )
            statement = (
                update(ConversationSummary)
                .where(*conditions)
                .values(**values)
            )

        result = await self.session.execute(statement)
        if result.rowcount != 1:
            await self.session.rollback()
            logger.info(
                "Conversation memory compaction lost optimistic update",
                extra={"conversation_id": str(conversation_id)},
            )
            return False

        await self.session.commit()
        return True

    async def upsert_documents_summary(
        self,
        conversation_id: UUID,
        documents_summary: str | None,
    ) -> None:
        now = datetime.now(UTC)
        statement = (
            insert(ConversationSummary)
            .values(
                conversation_id=conversation_id,
                documents_summary=documents_summary,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=[ConversationSummary.conversation_id],
                set_={
                    "documents_summary": documents_summary,
                    "updated_at": now,
                },
            )
        )
        await self.session.execute(statement)
        await self.session.commit()

    async def _get_summary_state(
        self,
        conversation_id: UUID,
    ) -> ConversationSummary | None:
        result = await self.session.execute(
            select(ConversationSummary).where(
                ConversationSummary.conversation_id == conversation_id
            )
        )
        return result.scalar_one_or_none()

    def _count_tokens(self, messages: list[Message]) -> int:
        try:
            encoding = tiktoken.encoding_for_model(
                self.settings.memory_summarization_model
            )
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        return sum(len(encoding.encode(message.text)) + 4 for message in messages)

    @staticmethod
    def _parse_summary(
        value: dict[str, object] | None,
    ) -> ConversationMemorySummary | None:
        if value is None:
            return None
        return ConversationMemorySummary.model_validate(value)

    @staticmethod
    def _to_langchain_message(message: Message) -> BaseMessage:
        if message.role == MessageRole.user:
            return HumanMessage(content=message.text)
        return AIMessage(content=message.text)
