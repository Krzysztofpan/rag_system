import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation
from app.db.models.document import Document
from app.services.doc_store import DocumentStore
from app.services.vector_store import VectorStore
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
logger = logging.getLogger(__name__)

class ConversationTitle(BaseModel):
    title: str = Field(description="Conversation title")

class ConversationService:
    """Every lookup is scoped to the owning user; `user_id` is never optional."""

    def __init__(
        self,
        session: AsyncSession,
        vector_store: VectorStore,
        doc_store: DocumentStore,
    ):
        self.session = session
        self.vector_store = vector_store
        self.doc_store = doc_store

    async def create_conversation(self, *, user_id: UUID) -> Conversation:
        conversation = Conversation(user_id=user_id, title="New Conversation")
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

        try:
            self.vector_store.delete_namespace(conversation_id)
        except Exception:
            logger.exception(
                "Pinecone namespace leftover after conversation delete: %s",
                conversation_id,
            )

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

        conversation.title = title
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation.title

    async def generate_conversation_title(self, conversation_id: UUID, doc_summary: str, *, user_id: UUID):
        template = """
        Based on actual title and new document summary you have to create new conversation title.
        Title should be general and short, it's just for user to know what is about:

        document summary: {doc_summary}

        current_title: {conversation_title}
        """

        prompt = ChatPromptTemplate.from_template(template)
        
        conversation = await self.get_conversation(conversation_id, user_id=user_id)

        summarization_llm = ChatOpenAI(model="gpt-4o-mini").with_structured_output(ConversationTitle)
  
        summary_chain = prompt | summarization_llm

        
        result = await summary_chain.ainvoke({"doc_summary": doc_summary, "conversation_title": conversation.title})

        await self.change_conversation_title(conversation_id, user_id=user_id, title=result.title)

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

    async def delete_document(
        self,
        conversation_id: UUID,
        document_id: UUID,
        *,
        user_id: UUID,
    ) -> Document:
        deleted = await self.doc_store.delete_document(
            conversation_id,
            document_id,
            user_id=user_id,
        )
        try:
            self.vector_store.delete_document_vectors(conversation_id, document_id)
        except Exception:
            logger.exception(
                "Pinecone vectors leftover after document delete: %s",
                document_id,
            )
        return deleted

    async def change_document_name(
        self,
        conversation_id: UUID,
        document_id: UUID,
        name: str,
        *,
        user_id: UUID,
    ) -> str:
        updated_name = await self.doc_store.change_document_name(
            conversation_id,
            document_id,
            name,
            user_id=user_id,
        )
        try:
            self.vector_store.update_document_source_filename(
                conversation_id,
                document_id,
                updated_name,
            )
        except Exception:
            logger.exception(
                "Pinecone source_filename leftover after document rename: %s",
                document_id,
            )
        return updated_name
