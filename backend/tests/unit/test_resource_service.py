from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.models.resource import Resource, ResourceType
from app.services.resource_service import (
    ResourceNotConvertibleError,
    ResourceNotEditableError,
    ResourceService,
)


def _session_with_resource(resource: Resource | None) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = resource
    session.execute = AsyncMock(return_value=result)
    return session


async def test_get_resource_returns_owned_row():
    resource = Resource(
        conversation_id=uuid4(),
        type=ResourceType.note,
        title="New Note",
        content={"kind": "user", "html": ""},
    )
    session = _session_with_resource(resource)
    service = ResourceService(session)

    result = await service.get_resource(
        resource.conversation_id,
        resource.id,
        user_id=uuid4(),
    )

    assert result is resource


async def test_get_resource_raises_when_missing_or_foreign():
    resource_id = uuid4()
    session = _session_with_resource(None)
    service = ResourceService(session)

    with pytest.raises(ValueError, match=f"Resource {resource_id} not found"):
        await service.get_resource(uuid4(), resource_id, user_id=uuid4())


async def test_update_note_content_replaces_user_html():
    resource = Resource(
        conversation_id=uuid4(),
        type=ResourceType.note,
        title="New Note",
        content={"kind": "user", "html": ""},
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    session = _session_with_resource(resource)
    service = ResourceService(session)
    content = {"kind": "user", "html": "<p>Saved</p>"}

    updated = await service.update_note_content(
        resource.conversation_id,
        resource.id,
        user_id=uuid4(),
        content=content,
    )

    assert updated is resource
    assert resource.content == content
    assert resource.updated_at > datetime(2026, 1, 1, tzinfo=UTC)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(resource)


async def test_update_note_content_rejects_chat_notes():
    resource = Resource(
        conversation_id=uuid4(),
        type=ResourceType.note,
        title="Pinned",
        content={"kind": "chat", "markdown": "# Hello"},
    )
    session = _session_with_resource(resource)
    service = ResourceService(session)

    with pytest.raises(ResourceNotEditableError, match="Only user notes can be updated"):
        await service.update_note_content(
            resource.conversation_id,
            resource.id,
            user_id=uuid4(),
            content={"kind": "user", "html": "<p>Nope</p>"},
        )

    session.commit.assert_not_awaited()


async def test_update_note_content_rejects_non_notes():
    resource = Resource(
        conversation_id=uuid4(),
        type=ResourceType.mind_map,
        title="Map",
        content={"nodes": []},
    )
    session = _session_with_resource(resource)
    service = ResourceService(session)

    with pytest.raises(ResourceNotEditableError, match="Only user notes can be updated"):
        await service.update_note_content(
            resource.conversation_id,
            resource.id,
            user_id=uuid4(),
            content={"kind": "user", "html": "<p>Nope</p>"},
        )

    session.commit.assert_not_awaited()


async def test_delete_resource_removes_owned_row():
    conversation_id = uuid4()
    resource = Resource(
        conversation_id=conversation_id,
        type=ResourceType.note,
        title="New Note",
        content={"kind": "user", "html": ""},
    )
    session = _session_with_resource(resource)
    service = ResourceService(session)

    deleted = await service.delete_resource(
        conversation_id,
        resource.id,
        user_id=uuid4(),
    )

    assert deleted is resource
    session.delete.assert_awaited_once_with(resource)
    session.commit.assert_awaited_once()


async def test_delete_resource_raises_when_missing():
    session = _session_with_resource(None)
    service = ResourceService(session)

    with pytest.raises(ValueError, match="Resource .* not found"):
        await service.delete_resource(uuid4(), uuid4(), user_id=uuid4())

    session.delete.assert_not_called()
    session.commit.assert_not_called()


async def test_get_note_source_payload_builds_markdown_from_user_note():
    resource = Resource(
        conversation_id=uuid4(),
        type=ResourceType.note,
        title="My Note",
        content={"kind": "user", "html": "<p>Hello</p>"},
    )
    session = _session_with_resource(resource)
    service = ResourceService(session)

    filename, markdown = await service.get_note_source_payload(
        resource.conversation_id,
        resource.id,
        user_id=uuid4(),
    )

    assert filename == "My Note.md"
    assert markdown == "# My Note\n\nHello\n"


async def test_get_note_source_payload_rejects_empty_note():
    resource = Resource(
        conversation_id=uuid4(),
        type=ResourceType.note,
        title="Empty",
        content={"kind": "user", "html": "<p><br></p>"},
    )
    session = _session_with_resource(resource)
    service = ResourceService(session)

    with pytest.raises(ResourceNotConvertibleError, match="Note has no content"):
        await service.get_note_source_payload(
            resource.conversation_id,
            resource.id,
            user_id=uuid4(),
        )


async def test_get_note_source_payload_rejects_non_notes():
    resource = Resource(
        conversation_id=uuid4(),
        type=ResourceType.mind_map,
        title="Map",
        content={"nodes": []},
    )
    session = _session_with_resource(resource)
    service = ResourceService(session)

    with pytest.raises(ResourceNotConvertibleError, match="Only notes can be converted"):
        await service.get_note_source_payload(
            resource.conversation_id,
            resource.id,
            user_id=uuid4(),
        )
