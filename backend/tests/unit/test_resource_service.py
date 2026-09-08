from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models.resource import Resource, ResourceType
from app.lib.note_markdown import DEFAULT_NOTE_TITLE
from app.services.resource_service import (
    ResourceNotConvertibleError,
    ResourceNotEditableError,
    ResourceService,
    chat_note_message_id,
)


def _session_with_resource(resource: Resource | None) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = resource
    session.execute = AsyncMock(return_value=result)
    return session


def _session_with_execute_results(*values: object) -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    results = []
    for value in values:
        result = MagicMock()
        result.scalar_one_or_none.return_value = value
        results.append(result)
    session.execute = AsyncMock(side_effect=results)
    return session


def test_chat_note_message_id_reads_chat_payload():
    message_id = uuid4()
    assert chat_note_message_id({
        "kind": "chat",
        "markdown": "# Hi",
        "message_id": str(message_id),
    }) == message_id
    assert chat_note_message_id({"kind": "user", "html": ""}) is None
    assert chat_note_message_id({"kind": "chat", "markdown": "# Hi"}) is None
    assert chat_note_message_id({"kind": "chat", "message_id": "not-a-uuid"}) is None


async def test_create_note_returns_existing_chat_pin():
    message_id = uuid4()
    resource = Resource(
        conversation_id=uuid4(),
        type=ResourceType.note,
        title="Pinned",
        content={
            "kind": "chat",
            "markdown": "# Hello",
            "message_id": str(message_id),
        },
    )
    session = _session_with_execute_results(resource)
    service = ResourceService(session)

    result, created = await service.create_note(
        resource.conversation_id,
        user_id=uuid4(),
        title="New Note",
        content=resource.content,
    )

    assert result is resource
    assert created is False
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


async def test_create_note_inserts_new_chat_pin():
    message_id = uuid4()
    conversation_id = uuid4()
    content = {
        "kind": "chat",
        "markdown": "# Hello",
        "message_id": str(message_id),
    }
    session = _session_with_execute_results(None, object())
    service = ResourceService(session)

    result, created = await service.create_note(
        conversation_id,
        user_id=uuid4(),
        title="New Note",
        content=content,
    )

    assert created is True
    assert result.conversation_id == conversation_id
    assert result.content == content
    session.add.assert_called_once_with(result)
    session.commit.assert_awaited_once()


async def test_create_user_note_skips_message_lookup():
    conversation_id = uuid4()
    content = {"kind": "user", "html": ""}
    session = _session_with_execute_results(object())
    service = ResourceService(session)

    result, created = await service.create_note(
        conversation_id,
        user_id=uuid4(),
        title="New Note",
        content=content,
    )

    assert created is True
    assert result.content == content
    assert session.execute.await_count == 1
    session.add.assert_called_once()
    session.commit.assert_awaited_once()


async def test_create_note_recovers_from_unique_violation():
    message_id = uuid4()
    conversation_id = uuid4()
    content = {
        "kind": "chat",
        "markdown": "# Hello",
        "message_id": str(message_id),
    }
    existing = Resource(
        conversation_id=conversation_id,
        type=ResourceType.note,
        title="Pinned",
        content=content,
    )
    session = _session_with_execute_results(None, object(), existing)
    session.commit = AsyncMock(side_effect=IntegrityError("", {}, Exception()))
    service = ResourceService(session)

    result, created = await service.create_note(
        conversation_id,
        user_id=uuid4(),
        title="New Note",
        content=content,
    )

    assert result is existing
    assert created is False
    session.rollback.assert_awaited_once()


async def test_create_note_reraises_integrity_error_without_existing_pin():
    message_id = uuid4()
    session = _session_with_execute_results(None, object(), None)
    session.commit = AsyncMock(side_effect=IntegrityError("", {}, Exception()))
    service = ResourceService(session)

    with pytest.raises(IntegrityError):
        await service.create_note(
            uuid4(),
            user_id=uuid4(),
            title="New Note",
            content={
                "kind": "chat",
                "markdown": "# Hello",
                "message_id": str(message_id),
            },
        )

    session.rollback.assert_awaited_once()


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


async def test_update_title_replaces_default_note_title():
    resource = Resource(
        conversation_id=uuid4(),
        type=ResourceType.note,
        title=DEFAULT_NOTE_TITLE,
        content={"kind": "chat", "markdown": "# Hello"},
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    session = _session_with_resource(resource)
    service = ResourceService(session)

    updated = await service.update_title(
        resource.conversation_id,
        resource.id,
        user_id=uuid4(),
        title="Invoice terms",
    )

    assert updated is resource
    assert resource.title == "Invoice terms"
    assert resource.updated_at > datetime(2026, 1, 1, tzinfo=UTC)
    session.commit.assert_awaited_once()


async def test_update_title_keeps_custom_title():
    resource = Resource(
        conversation_id=uuid4(),
        type=ResourceType.note,
        title="Pinned recap",
        content={"kind": "chat", "markdown": "# Hello"},
    )
    session = _session_with_resource(resource)
    service = ResourceService(session)

    updated = await service.update_title(
        resource.conversation_id,
        resource.id,
        user_id=uuid4(),
        title="Invoice terms",
    )

    assert updated is resource
    assert resource.title == "Pinned recap"
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
