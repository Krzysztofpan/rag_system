"""API tests for authenticated resource routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.deps import AuthenticatedUser, get_current_user
from app.container import get_usage_limit_service, get_vector_store
from app.db.models.resource import Resource, ResourceType
from app.db.session import get_session
from app.lib.rate_limit import configure_rate_limiting, limiter
from app.routes.resource_routes import resource_router
from app.services.resource_service import ResourceNotEditableError
from app.services.usage_limits import LimitCode, LimitExceededError
from tests.helpers import FakeVectorStore, override_authenticated_user


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def authenticated_user(user_id):
    return AuthenticatedUser(
        access_token="test-token",
        user_id=user_id,
        email="user@example.com",
        role="authenticated",
        phone=None,
        app_metadata={},
        user_metadata={},
    )


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def apply_note_title():
    with patch(
        "app.routes.resource_routes.apply_note_title",
        new=AsyncMock(),
    ) as mock:
        yield mock


@pytest.fixture
def usage_limits():
    service = AsyncMock()
    service.enabled = True
    service.settings.max_chat_notes_per_day = 3
    return service


@pytest.fixture
def client(authenticated_user, mock_session, apply_note_title, usage_limits):
    limiter.reset()
    app = FastAPI()
    configure_rate_limiting(app)
    app.include_router(resource_router)

    async def override_session():
        yield mock_session

    app.dependency_overrides[get_current_user] = override_authenticated_user(
        authenticated_user
    )
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_vector_store] = lambda: FakeVectorStore()
    app.dependency_overrides[get_usage_limit_service] = lambda: usage_limits

    with TestClient(app) as test_client:
        yield test_client


def test_resource_routes_require_authentication():
    app = FastAPI()
    app.include_router(resource_router)

    with TestClient(app) as test_client:
        response = test_client.get(f"/conversations/{uuid4()}/resources")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_create_note_defaults_to_user_html(client, apply_note_title, usage_limits):
    conversation_id = uuid4()
    resource = Resource(
        conversation_id=conversation_id,
        type=ResourceType.note,
        title="New Note",
        content={"kind": "user", "html": ""},
    )

    with patch(
        "app.services.resource_service.ResourceService.create_resource",
        new=AsyncMock(return_value=resource),
    ) as create_resource:
        response = client.post(f"/conversations/{conversation_id}/resources/note", json={})

    assert response.status_code == 200
    assert response.json()["resource"]["content"] == {"kind": "user", "html": ""}
    assert create_resource.await_args.kwargs["content"] == {"kind": "user", "html": ""}
    apply_note_title.assert_not_awaited()
    usage_limits.enforce_create_chat_note.assert_not_awaited()


def test_create_chat_note_stores_markdown(client, apply_note_title, authenticated_user, usage_limits):
    conversation_id = uuid4()
    message_id = uuid4()
    chunk_id = uuid4()
    source = {"index": 1, "kind": "chunk", "chunk_id": str(chunk_id)}
    resource = Resource(
        conversation_id=conversation_id,
        type=ResourceType.note,
        title="New Note",
        content={
            "kind": "chat",
            "markdown": "# Hello",
            "message_id": str(message_id),
            "sources": [source],
        },
    )

    with patch(
        "app.services.resource_service.ResourceService.find_chat_note_by_message_id",
        new=AsyncMock(return_value=None),
    ), patch(
        "app.services.resource_service.ResourceService.create_resource",
        new=AsyncMock(return_value=resource),
    ) as create_resource:
        response = client.post(
            f"/conversations/{conversation_id}/resources/note",
            json={
                "title": "",
                "content": {
                    "kind": "chat",
                    "markdown": "# Hello",
                    "messageId": str(message_id),
                    "sources": [{
                        "index": 1,
                        "kind": "chunk",
                        "chunkId": str(chunk_id),
                    }],
                },
            },
        )

    assert response.status_code == 200
    assert response.json()["resource"]["content"] == {
        "kind": "chat",
        "markdown": "# Hello",
        "messageId": str(message_id),
        "sources": [{
            "index": 1,
            "kind": "chunk",
            "chunkId": str(chunk_id),
        }],
    }
    assert create_resource.await_args.kwargs["content"] == {
        "kind": "chat",
        "markdown": "# Hello",
        "message_id": str(message_id),
        "sources": [source],
    }
    apply_note_title.assert_awaited_once_with(
        conversation_id,
        resource.id,
        authenticated_user.user_id,
    )
    usage_limits.enforce_create_chat_note.assert_awaited_once_with(
        authenticated_user.user_id
    )


def test_create_chat_note_with_custom_title_skips_title_generation(client, apply_note_title):
    conversation_id = uuid4()
    resource = Resource(
        conversation_id=conversation_id,
        type=ResourceType.note,
        title="Pinned recap",
        content={"kind": "chat", "markdown": "# Hello"},
    )

    with patch(
        "app.services.resource_service.ResourceService.create_resource",
        new=AsyncMock(return_value=resource),
    ):
        response = client.post(
            f"/conversations/{conversation_id}/resources/note",
            json={
                "title": "Pinned recap",
                "content": {"kind": "chat", "markdown": "# Hello"},
            },
        )

    assert response.status_code == 200
    apply_note_title.assert_not_awaited()


def test_create_chat_note_returns_existing_without_title_generation(
    client, apply_note_title, usage_limits
):
    conversation_id = uuid4()
    message_id = uuid4()
    resource = Resource(
        conversation_id=conversation_id,
        type=ResourceType.note,
        title="Invoice terms",
        content={
            "kind": "chat",
            "markdown": "# Hello",
            "message_id": str(message_id),
        },
    )

    with patch(
        "app.services.resource_service.ResourceService.find_chat_note_by_message_id",
        new=AsyncMock(return_value=resource),
    ) as find_chat_note, patch(
        "app.services.resource_service.ResourceService.create_resource",
        new=AsyncMock(),
    ) as create_resource:
        response = client.post(
            f"/conversations/{conversation_id}/resources/note",
            json={
                "content": {
                    "kind": "chat",
                    "markdown": "# Hello",
                    "messageId": str(message_id),
                },
            },
        )

    assert response.status_code == 200
    assert response.json()["resource"]["id"] == str(resource.id)
    assert response.json()["resource"]["title"] == "Invoice terms"
    find_chat_note.assert_awaited_once()
    create_resource.assert_not_awaited()
    apply_note_title.assert_not_awaited()
    usage_limits.enforce_create_chat_note.assert_not_awaited()


def test_create_chat_note_limit_returns_429(client, usage_limits):
    conversation_id = uuid4()
    message_id = uuid4()
    usage_limits.enforce_create_chat_note.side_effect = LimitExceededError(
        LimitCode.max_chat_notes_per_day,
        limit=3,
        current=3,
        message="Daily chat note limit reached (3).",
    )

    with patch(
        "app.services.resource_service.ResourceService.find_chat_note_by_message_id",
        new=AsyncMock(return_value=None),
    ), patch(
        "app.services.resource_service.ResourceService.create_resource",
        new=AsyncMock(),
    ) as create_resource:
        response = client.post(
            f"/conversations/{conversation_id}/resources/note",
            json={
                "content": {
                    "kind": "chat",
                    "markdown": "# Hello",
                    "messageId": str(message_id),
                },
            },
        )

    assert response.status_code == 429
    payload = response.json()["detail"]
    assert payload["code"] == "max_chat_notes_per_day"
    assert payload["limit"] == 3
    assert payload["current"] == 3
    create_resource.assert_not_awaited()


def test_update_note_saves_user_html(client):
    conversation_id = uuid4()
    resource = Resource(
        conversation_id=conversation_id,
        type=ResourceType.note,
        title="New Note",
        content={"kind": "user", "html": "<p>Saved</p>"},
    )

    with patch(
        "app.services.resource_service.ResourceService.update_note_content",
        new=AsyncMock(return_value=resource),
    ) as update_note_content:
        response = client.patch(
            f"/conversations/{conversation_id}/resources/note/{resource.id}",
            json={"content": {"kind": "user", "html": "<p>Saved</p>"}},
        )

    assert response.status_code == 200
    assert response.json()["resource"]["content"] == {"kind": "user", "html": "<p>Saved</p>"}
    assert update_note_content.await_args.kwargs["content"] == {
        "kind": "user",
        "html": "<p>Saved</p>",
    }


def test_update_note_not_found_returns_404(client):
    conversation_id = uuid4()
    resource_id = uuid4()

    with patch(
        "app.services.resource_service.ResourceService.update_note_content",
        new=AsyncMock(side_effect=ValueError("Resource not found")),
    ):
        response = client.patch(
            f"/conversations/{conversation_id}/resources/note/{resource_id}",
            json={"content": {"html": "<p>Hi</p>"}},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found"


def test_update_chat_note_returns_400(client):
    conversation_id = uuid4()
    resource_id = uuid4()

    with patch(
        "app.services.resource_service.ResourceService.update_note_content",
        new=AsyncMock(side_effect=ResourceNotEditableError("Only user notes can be updated")),
    ):
        response = client.patch(
            f"/conversations/{conversation_id}/resources/note/{resource_id}",
            json={"content": {"html": "<p>Hi</p>"}},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only user notes can be updated"


def test_delete_resource_returns_deleted_resource(client):
    conversation_id = uuid4()
    resource = Resource(
        conversation_id=conversation_id,
        type=ResourceType.note,
        title="New Note",
        content={"kind": "user", "html": "<p>Hi</p>"},
    )

    with patch(
        "app.services.resource_service.ResourceService.delete_resource",
        new=AsyncMock(return_value=resource),
    ):
        response = client.delete(
            f"/conversations/{conversation_id}/resources/{resource.id}"
        )

    assert response.status_code == 200
    payload = response.json()["deletedResource"]
    assert payload["id"] == str(resource.id)
    assert payload["title"] == "New Note"
    assert payload["content"] == {"kind": "user", "html": "<p>Hi</p>"}


def test_delete_resource_not_found_returns_404(client):
    conversation_id = uuid4()
    resource_id = uuid4()

    with patch(
        "app.services.resource_service.ResourceService.delete_resource",
        new=AsyncMock(side_effect=ValueError("Resource missing")),
    ):
        response = client.delete(
            f"/conversations/{conversation_id}/resources/{resource_id}"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource missing"
