from datetime import datetime
from typing import Annotated, Any, Literal, Optional
from uuid import UUID

from pydantic import Field, TypeAdapter, ValidationError, field_validator

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


def coerce_stored_note_content(content: dict[str, Any] | None) -> dict[str, Any]:
    """Map stored JSONB (including legacy `{text}`) into a NoteContent dict."""
    if not content:
        return {"kind": "user", "html": ""}
    if "kind" not in content and "text" in content:
        return {"kind": "chat", "markdown": str(content.get("text") or "")}
    return content


def parse_note_content(content: dict[str, Any] | None) -> ChatNoteContent | UserNoteContent:
    return _note_content_adapter.validate_python(coerce_stored_note_content(content))


def dump_note_content(
    content: ChatNoteContent | UserNoteContent,
    *,
    by_alias: bool,
) -> dict[str, Any]:
    return content.model_dump(mode="json", by_alias=by_alias, exclude_none=True)


def note_content_for_response(content: dict[str, Any] | None) -> dict[str, Any]:
    try:
        return dump_note_content(parse_note_content(content), by_alias=True)
    except ValidationError:
        return dump_note_content(UserNoteContent(), by_alias=True)


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

    @field_validator("content", mode="before")
    @classmethod
    def coerce_legacy_content(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (ChatNoteContent, UserNoteContent)):
            return value
        if isinstance(value, dict):
            return coerce_stored_note_content(value)
        return value


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
