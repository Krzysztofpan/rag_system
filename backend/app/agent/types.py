from typing import TypedDict
from uuid import UUID

from app.schemas.citation_source import MessageSource


class AgentContext(TypedDict):
    conversation_id: UUID
    user_id: UUID
    document_ids: list[UUID]
    user_query: str
    sources: list[MessageSource]
