from __future__ import annotations

from enum import StrEnum
from typing import NoReturn
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models.conversation import Conversation
from app.db.models.message import Message


class LimitCode(StrEnum):
    max_upload_bytes = "max_upload_bytes"
    max_ingests_per_day = "max_ingests_per_day"
    max_messages_per_day = "max_messages_per_day"
    max_conversations = "max_conversations"
    max_messages_per_conversation = "max_messages_per_conversation"


class LimitExceededError(Exception):
    def __init__(
        self,
        code: LimitCode,
        *,
        limit: int,
        current: int,
        message: str,
    ) -> None:
        self.code = code
        self.limit = limit
        self.current = current
        super().__init__(message)

    @property
    def status_code(self) -> int:
        if self.code is LimitCode.max_upload_bytes:
            return 413
        return 429

    def as_detail(self) -> dict[str, str | int]:
        return {
            "code": self.code.value,
            "message": str(self),
            "limit": self.limit,
            "current": self.current,
        }


class UsageLimitService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return bool(getattr(self.settings, "limits_enabled", False))

    def raise_upload_too_large(self, *, size: int) -> NoReturn:
        limit = self.settings.max_upload_bytes
        raise LimitExceededError(
            LimitCode.max_upload_bytes,
            limit=limit,
            current=size,
            message=f"File exceeds the {limit} byte upload limit.",
        )

    async def enforce_create_conversation(self, user_id: UUID) -> None:
        if not self.enabled:
            return
        result = await self.session.execute(
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.user_id == user_id)
        )
        current = result.scalar_one()
        limit = self.settings.max_conversations
        if current >= limit:
            raise LimitExceededError(
                LimitCode.max_conversations,
                limit=limit,
                current=current,
                message=f"Conversation limit reached ({limit}).",
            )

    async def enforce_conversation_messages(self, conversation_id: UUID) -> None:
        if not self.enabled:
            return
        result = await self.session.execute(
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conversation_id)
        )
        current = result.scalar_one()
        limit = self.settings.max_messages_per_conversation
        if current >= limit:
            raise LimitExceededError(
                LimitCode.max_messages_per_conversation,
                limit=limit,
                current=current,
                message=f"This conversation has reached the {limit} message limit.",
            )
