from pydantic import BaseModel, Field
from uuid import UUID

class ChatRequestBody(BaseModel):
    conversation_id: UUID
    message: str = Field(min_length=1, max_length=1000)
    document_ids: list[UUID] = Field(default_factory=list)