from app.db.models import Message
from app.schemas.base import APIModel

class GetConversationMessagesResponse(APIModel):
    messages: list[Message]
    has_more: bool
