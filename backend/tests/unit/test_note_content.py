from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.db.models.resource import Resource, ResourceType
from app.schemas.resource import (
    ChatNoteContent,
    CreateNoteRequest,
    UserNoteContent,
    dump_note_content,
    resource_from_model,
)


def test_user_and_chat_notes_dump_for_storage_and_api():
    message_id = uuid4()
    chat = ChatNoteContent(markdown="# Hi", message_id=message_id)
    user = UserNoteContent(html="<p>Hi</p>")

    assert dump_note_content(chat, by_alias=False) == {
        "kind": "chat",
        "markdown": "# Hi",
        "message_id": str(message_id),
        "sources": [],
    }
    assert dump_note_content(chat, by_alias=True) == {
        "kind": "chat",
        "markdown": "# Hi",
        "messageId": str(message_id),
        "sources": [],
    }
    assert dump_note_content(user, by_alias=True) == {
        "kind": "user",
        "html": "<p>Hi</p>",
    }


def test_create_note_request_accepts_omitted_content():
    request = CreateNoteRequest.model_validate({"title": "New Note"})
    assert request.content is None


def test_create_note_request_rejects_unknown_kind():
    with pytest.raises(ValidationError):
        CreateNoteRequest.model_validate({"content": {"kind": "other", "html": ""}})
    with pytest.raises(ValidationError):
        CreateNoteRequest.model_validate({"content": {}})
    with pytest.raises(ValidationError):
        CreateNoteRequest.model_validate({"content": {"text": "pinned"}})


def test_resource_from_model_dumps_valid_chat_note():
    resource = Resource(
        conversation_id=uuid4(),
        type=ResourceType.note,
        title="Pinned",
        content={"kind": "chat", "markdown": "## Section"},
    )
    response = resource_from_model(resource)
    assert response.content == {
        "kind": "chat",
        "markdown": "## Section",
        "sources": [],
    }


def test_chat_note_roundtrips_citation_sources():
    chunk_id = uuid4()
    parsed = ChatNoteContent.model_validate({
        "kind": "chat",
        "markdown": "See [1](/citation/1).",
        "sources": [{"index": 1, "kind": "chunk", "chunkId": str(chunk_id)}],
    })

    assert dump_note_content(parsed, by_alias=False) == {
        "kind": "chat",
        "markdown": "See [1](/citation/1).",
        "sources": [{"index": 1, "kind": "chunk", "chunk_id": str(chunk_id)}],
    }
    assert dump_note_content(parsed, by_alias=True)["sources"] == [
        {"index": 1, "kind": "chunk", "chunkId": str(chunk_id)},
    ]


def test_resource_from_model_leaves_mind_map_content():
    resource = Resource(
        conversation_id=uuid4(),
        type=ResourceType.mind_map,
        title="Map",
        content={"nodes": []},
    )
    response = resource_from_model(resource)
    assert response.content == {"nodes": []}
