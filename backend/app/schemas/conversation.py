from uuid import UUID

from app.schemas.base import APIModel


class CreateConversationRequest(APIModel):
    user_id: UUID


class CreateConversationResponse(APIModel):
    conversation_id: str
    user_id: str
