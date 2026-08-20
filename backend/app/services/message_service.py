from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Message
from app.db.models.conversation import Conversation


@dataclass(frozen=True)
class MessagePage:
    messages: list[Message]
    has_more: bool


class MessageService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_message(self, message: Message) -> Message:
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_messages(
        self,
        conversation_id: UUID,
        *,
        user_id: UUID,
        limit: int = 20,
        before_id: UUID | None = None,
    ) -> MessagePage:
        query = (
            select(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Message.conversation_id == conversation_id,
                Conversation.user_id == user_id,
            )
        )

        if before_id is not None:
            cursor_result = await self.session.execute(
                select(Message.created_at, Message.id).where(
                    Message.id == before_id,
                    Message.conversation_id == conversation_id,
                )
            )
            cursor = cursor_result.one_or_none()
            if cursor is None:
                raise ValueError(f"Message {before_id} not found")

            query = query.where(
                (Message.created_at < cursor.created_at)
                | (
                    (Message.created_at == cursor.created_at)
                    & (Message.id < cursor.id)
                )
            )

        query = query.order_by(Message.created_at.desc(), Message.id.desc()).limit(
            limit + 1
        )
        result = await self.session.execute(query)
        rows = list(result.scalars().all())
        has_more = len(rows) > limit
        messages = rows[:limit]
        messages.reverse()
        return MessagePage(messages=messages, has_more=has_more)

    async def get_messages_after(
        self,
        conversation_id: UUID,
        *,
        user_id: UUID,
        after_id: UUID | None,
        limit: int,
        newest_first: bool = False,
    ) -> list[Message]:
        query = (
            select(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Message.conversation_id == conversation_id,
                Conversation.user_id == user_id,
            )
        )

        if after_id is not None:
            cursor_result = await self.session.execute(
                select(Message.created_at, Message.id)
                .join(Conversation, Conversation.id == Message.conversation_id)
                .where(
                    Message.id == after_id,
                    Message.conversation_id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
            cursor = cursor_result.one_or_none()
            if cursor is None:
                raise ValueError(f"Message {after_id} not found")
            query = query.where(
                (Message.created_at > cursor.created_at)
                | (
                    (Message.created_at == cursor.created_at)
                    & (Message.id > cursor.id)
                )
            )

        if newest_first:
            query = query.order_by(Message.created_at.desc(), Message.id.desc())
        else:
            query = query.order_by(Message.created_at.asc(), Message.id.asc())

        result = await self.session.execute(query.limit(limit))
        messages = list(result.scalars().all())
        if newest_first:
            messages.reverse()
        return messages
