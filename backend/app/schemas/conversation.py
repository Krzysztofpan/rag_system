from __future__ import annotations

from datetime import datetime

from app.db.models.conversation import Conversation
from app.schemas.base import APIModel


class ConversationResponse(APIModel):
    id: str
    created_at: datetime
    updated_at: datetime
    user_id: str
    source_count: int
    title: str | None = None


class GetConversationsResponse(APIModel):
    conversations: list[ConversationResponse]

class DeleteConversationResponse(APIModel):
    deleted_conversation: ConversationResponse


class CreateConversationResponse(APIModel):
    conversation_id: str
    user_id: str


def conversation_from_model(conversation: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=str(conversation.id),
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        user_id=str(conversation.user_id),
        source_count=conversation.source_count,
        title=conversation.title,
    )
