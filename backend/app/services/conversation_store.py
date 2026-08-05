from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.models.conversation import Conversation
from app.db.models.document import Document
from sqlalchemy import select

class ConversationStore:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_conversation(self, *, user_id: UUID) -> Conversation:
        conversation = Conversation(user_id=user_id)
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def get_conversation(self, conversation_id: UUID) -> Conversation:
        conversation = await self.session.get(Conversation, conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        return conversation

    async def get_conversation_documents(self, conversation_id: UUID) -> List[Document]:
        result = await self.session.execute(
            select(Document).where(Document.conversation_id == conversation_id)
        )

        documents = list(result.scalars().all())

        if documents is None:
            return []

        return documents
