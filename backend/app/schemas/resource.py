from datetime import datetime
from typing import Annotated, Any, Literal, Optional
from uuid import UUID

from pydantic import Field, TypeAdapter, ValidationError

from app.db.models import Resource, ResourceType
from app.schemas.base import APIModel
from app.schemas.message_source import MessageSource


class ChatNoteContent(APIModel):
    kind: Literal["chat"] = "chat"
    markdown: str
    message_id: UUID | None = None
    sources: list[MessageSource] = Field(default_factory=list)


class UserNoteContent(APIModel):
    kind: Literal["user"] = "user"
    html: str = ""


NoteContent = Annotated[
    ChatNoteContent | UserNoteContent,
    Field(discriminator="kind"),
]

_note_content_adapter = TypeAdapter(NoteContent)


def dump_note_content(
    content: ChatNoteContent | UserNoteContent,
    *,
    by_alias: bool,
) -> dict[str, Any]:
    return content.model_dump(mode="json", by_alias=by_alias, exclude_none=True)


def note_content_for_response(content: dict[str, Any] | None) -> dict[str, Any]:
    try:
        parsed = _note_content_adapter.validate_python(content)
    except ValidationError:
        parsed = UserNoteContent()
    return dump_note_content(parsed, by_alias=True)


class ResourceResponse(APIModel):
    id: str
    type: ResourceType
    content: dict[str, Any]
    title: str
    created_at: datetime
    updated_at: datetime


class GetResourcesResponse(APIModel):
    count: int
    conversation_resources: list[ResourceResponse]


class CreateNoteRequest(APIModel):
    title: Optional[str] = None
    content: Optional[NoteContent] = None


class CreateResourceResponse(APIModel):
    resource: ResourceResponse


def resource_from_model(resource: Resource) -> ResourceResponse:
    content: dict[str, Any] = resource.content
    if resource.type == ResourceType.note:
        content = note_content_for_response(resource.content)
    return ResourceResponse(
        id=str(resource.id),
        type=resource.type,
        content=content,
        title=resource.title,
        created_at=resource.created_at,
        updated_at=resource.updated_at,
    )
