from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import Message
from app.schemas.base import APIModel


class ChatRequestBody(BaseModel):
    conversation_id: UUID
    message: str = Field(min_length=1, max_length=1000)
    document_ids: list[UUID] = Field(default_factory=list)
    message_id: UUID | None = None


class ChatResponseModel(APIModel):
    response: Message


class ProtocolCommand(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int = Field(ge=0)
    method: str
    params: dict[str, Any] = Field(default_factory=dict)


class StreamSubscriptionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    channels: list[str] = Field(default_factory=list)
    namespaces: list[list[str]] | None = None
    depth: int | None = Field(default=None, ge=0)
    since: int | None = Field(default=None, ge=0)


class StreamHumanMessage(BaseModel):
    id: UUID
    type: Literal["human"] = "human"
    content: str = Field(min_length=1, max_length=1000)


class ChatRunInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    messages: list[StreamHumanMessage]
    document_ids: list[UUID] = Field(default_factory=list, alias="documentIds")