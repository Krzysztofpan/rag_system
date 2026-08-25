from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.schemas.base import APIModel
from app.schemas.message_source import MessageSource


class MessageResponse(APIModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        from_attributes=True,
    )

    id: UUID
    conversation_id: UUID
    text: str
    role: str
    created_at: datetime
    sources: list[MessageSource] = Field(default_factory=list)


class GetConversationMessagesResponse(APIModel):
    messages: list[MessageResponse]
    has_more: bool
