from typing import TypedDict
from uuid import UUID

class AgentContext(TypedDict):
    conversation_id: UUID
    user_id: UUID
    document_ids: list[UUID]
    user_query: str
