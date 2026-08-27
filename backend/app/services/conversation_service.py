import logging
from typing import List
from uuid import UUID

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import ConversationTopicName
from app.db.models.conversation import Conversation
from app.prompts import CONVERSATION_TITLE_TEMPLATE, CONVERSATION_TOPIC_TEMPLATE
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class ConversationTitle(BaseModel):
    title: str = Field(description="Conversation title")


class ConversationTopic(BaseModel):
    topic: ConversationTopicName = Field(
        description=(
            "Document topic. If the document is not related to any of the topics, "
            "return 'general'."
        ),
    )


class ConversationService:
    """Every lookup is scoped to the owning user; `user_id` is never optional."""

    def __init__(
        self,
        session: AsyncSession,
        vector_store: VectorStore,
    ):
        self.session = session
        self.vector_store = vector_store

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
            select(Conversation).where(Conversation.user_id==user_id).order_by(Conversation.updated_at.desc())
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

    async def generate_conversation_title(self, conversation_id: UUID, doc_summary: str, *, user_id: UUID) -> str:
        prompt = ChatPromptTemplate.from_template(CONVERSATION_TITLE_TEMPLATE)

        conversation = await self.get_conversation(conversation_id, user_id=user_id)

        summarization_llm = ChatOpenAI(model="gpt-4o-mini").with_structured_output(ConversationTitle)

        summary_chain = prompt | summarization_llm


        result = await summary_chain.ainvoke(
            {"doc_summary": doc_summary, "conversation_title": conversation.title},
            config={"run_name": "generate_conversation_title"},
        )

        await self.change_conversation_title(
            conversation_id,
            user_id=user_id,
            title=result.title,
        )
        return result.title

    async def update_from_summary(
        self,
        conversation_id: UUID,
        doc_summary: str,
        *,
        user_id: UUID,
    ) -> str:
        title = await self.generate_conversation_title(
            conversation_id,
            doc_summary,
            user_id=user_id,
        )
        await self.generate_conversation_topic(
            conversation_id,
            doc_summary,
            user_id=user_id,
        )
        return title

    async def change_conversation_topic(
        self,
        conversation_id: UUID,
        *,
        user_id: UUID,
        topic: ConversationTopicName,
    ) -> ConversationTopicName:
        conversation = await self.get_conversation(conversation_id, user_id=user_id)
        conversation.topic = topic
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation.topic

    async def generate_conversation_topic(
        self,
        conversation_id: UUID,
        doc_summary: str,
        *,
        user_id: UUID,
    ) -> ConversationTopicName:
        prompt = ChatPromptTemplate.from_template(CONVERSATION_TOPIC_TEMPLATE)
        topic_llm = ChatOpenAI(model="gpt-4o-mini").with_structured_output(ConversationTopic)
        topic_chain = prompt | topic_llm
        result = await topic_chain.ainvoke(
            {"doc_summary": doc_summary},
            config={"run_name": "generate_conversation_topic"},
        )
        await self.change_conversation_topic(
            conversation_id,
            user_id=user_id,
            topic=result.topic,
        )
        return result.topic