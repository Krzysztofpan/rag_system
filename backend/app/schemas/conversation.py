from app.schemas.base import APIModel


class CreateConversationResponse(APIModel):
    conversation_id: str
    user_id: str
