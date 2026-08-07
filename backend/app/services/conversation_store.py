from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation
from app.db.models.document import Document
from typing import List

class ConversationStore:
    """Every lookup is scoped to the owning user; `user_id` is never optional."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_conversation(self, *, user_id: UUID) -> Conversation:
        conversation = Conversation(user_id=user_id, conversation_title="New Conversation")
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def get_conversations(
            self, *, user_id: UUID
    ) -> List[Conversation]:
        result = await self.session.execute(
            select(Conversation).where(Conversation.user_id==user_id)
        )

        return list(result.scalars().all())
 
    async def get_conversation(
        self,
        conversation_id: UUID,
        *,
        user_id: UUID,
    ) -> Conversation:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        conversation = result.scalar_one_or_none()

        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        return conversation

    async def delete_conversation(
        self,
        conversation_id: UUID,
        *,
        user_id: UUID,
    ) -> Conversation:
        conversation = await self.get_conversation(conversation_id, user_id=user_id)

        await self.session.delete(conversation)
        await self.session.commit()

        return conversation

    async def change_conversation_title(
        self,
        conversation_id: UUID,
        *,
        user_id: UUID,
        title: str
    ):
        conversation = await self.get_conversation(
           conversation_id, 
           user_id=user_id
        )
       
        if not title:
            raise ValueError("You have to define new title.")

        conversation.conversation_title = title
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation.conversation_title

    async def get_conversation_documents(
        self,
        conversation_id: UUID,
        *,
        user_id: UUID,
    ) -> list[Document]:
        await self.get_conversation(conversation_id, user_id=user_id)
        result = await self.session.execute(
            select(Document).where(Document.conversation_id == conversation_id)
        )
        return list(result.scalars().all())
