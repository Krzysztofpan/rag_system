"""API tests for ingest routes."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.deps import AuthenticatedUser, get_current_user
from app.container import (
    get_ingest_queue,
    get_usage_limit_service,
    get_vector_store,
)
from app.db.models.document import Document, DocumentStatus
from app.db.models.resource import Resource, ResourceType
from app.db.session import get_session
from app.lib.exceptions import register_limit_exceeded_handler
from app.lib.rate_limit import configure_rate_limiting, limiter
from app.lib.upload_temp import UploadTooLargeError
from app.routes.ingest_routes import ingest_router
from tests.helpers import FakeVectorStore, override_authenticated_user


def _mark_processing(document: Document) -> AsyncMock:
    async def mark_processing(_document_id):
        document.status = DocumentStatus.processing
        return document

    return AsyncMock(side_effect=mark_processing)


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
def usage_limits():
    service = AsyncMock()
    service.enabled = True
    service.settings.max_upload_bytes = 5 * 1024 * 1024
    return service


@pytest.fixture
def ingest_queue():
    queue = AsyncMock()
    queue.enqueue = AsyncMock()
    return queue


@pytest.fixture
def client(authenticated_user, mock_session, usage_limits, ingest_queue):
    limiter.reset()
    app = FastAPI()
    configure_rate_limiting(app)
    register_limit_exceeded_handler(app)
    app.include_router(ingest_router)

    async def override_session():
        yield mock_session

    app.dependency_overrides[get_current_user] = override_authenticated_user(
        authenticated_user
    )
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_vector_store] = lambda: FakeVectorStore()
    app.dependency_overrides[get_usage_limit_service] = lambda: usage_limits
    app.dependency_overrides[get_ingest_queue] = lambda: ingest_queue

    with TestClient(app) as test_client:
        yield test_client


def test_ingest_routes_require_authentication():
    app = FastAPI()
    app.include_router(ingest_router)

    with TestClient(app) as test_client:
        response = test_client.post(
            f"/ingest/{uuid4()}/url",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9wgXcQ"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_ingest_source_url_rejects_invalid_url_without_creating_document(client):
    conversation_id = uuid4()

    with patch(
        "app.services.document.document_service.DocumentService.create_document",
        new=AsyncMock(),
    ) as create_document:
        response = client.post(
            f"/ingest/{conversation_id}/url",
            json={"url": "https://example.com/watch?v=dQw4w9wgXcQ"},
        )

    assert response.status_code == 400
    create_document.assert_not_called()


def test_ingest_source_url_returns_202_and_enqueues_job(
    client,
    authenticated_user,
    ingest_queue,
    usage_limits,
):
    conversation_id = uuid4()
    document = Document(
        conversation_id=conversation_id,
        filename="youtube:dQw4w9wgXcQ",
        content_type="video/youtube",
        status=DocumentStatus.pending,
    )

    with (
        patch(
            "app.services.conversation.conversation_service.ConversationService.get_conversation",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "app.services.document.document_service.DocumentService.create_document",
            new=AsyncMock(return_value=document),
        ) as create_document,
        patch(
            "app.services.document.document_service.DocumentService.mark_processing",
            new=_mark_processing(document),
        ),
    ):
        response = client.post(
            f"/ingest/{conversation_id}/url",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9wgXcQ"},
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["id"] == str(document.id)
    assert payload["status"] == "processing"
    assert payload["contentType"] == "video/youtube"
    assert payload["filename"] == "youtube:dQw4w9wgXcQ"
    origin = create_document.await_args.kwargs["origin"]
    assert origin.kind == "youtube"
    assert origin.video_id == "dQw4w9wgXcQ"
    assert origin.url == "https://www.youtube.com/watch?v=dQw4w9wgXcQ"
    ingest_queue.enqueue.assert_awaited_once()
    job = ingest_queue.enqueue.await_args.args[0]
    assert job.kind == "youtube"
    assert job.document_id == document.id
    assert job.user_id == authenticated_user.user_id
    assert job.video_id == "dQw4w9wgXcQ"


def test_ingest_source_document_rejects_unsupported_type_without_creating_document(client):
    conversation_id = uuid4()

    with patch(
        "app.services.document.document_service.DocumentService.create_document",
        new=AsyncMock(),
    ) as create_document:
        response = client.post(
            f"/ingest/{conversation_id}/document",
            files={"file": ("archive.zip", b"PK", "application/zip")},
        )

    assert response.status_code == 400
    create_document.assert_not_called()


def test_ingest_source_document_returns_202_and_enqueues_job(
    client,
    authenticated_user,
    ingest_queue,
    usage_limits,
):
    conversation_id = uuid4()
    document = Document(
        conversation_id=conversation_id,
        filename="note.md",
        content_type="text/markdown",
        status=DocumentStatus.pending,
    )
    tmp_path = Path("/tmp/fake-note.md")

    with (
        patch(
            "app.services.conversation.conversation_service.ConversationService.get_conversation",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "app.services.document.document_service.DocumentService.create_document",
            new=AsyncMock(return_value=document),
        ) as create_document,
        patch(
            "app.services.document.document_service.DocumentService.mark_processing",
            new=_mark_processing(document),
        ),
        patch(
            "app.routes.ingest_routes.save_upload_to_temp",
            new=AsyncMock(return_value=(tmp_path, 12)),
        ),
    ):
        response = client.post(
            f"/ingest/{conversation_id}/document",
            files={"file": ("note.md", b"# hello world", "text/markdown")},
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["id"] == str(document.id)
    assert payload["status"] == "processing"
    assert payload["contentType"] == "text/markdown"
    assert payload["filename"] == "note.md"
    origin = create_document.await_args.kwargs["origin"]
    assert origin.kind == "file"
    assert origin.file_size_bytes == 12
    ingest_queue.enqueue.assert_awaited_once()
    job = ingest_queue.enqueue.await_args.args[0]
    assert job.kind == "document"
    assert job.document_id == document.id
    assert job.user_id == authenticated_user.user_id
    assert job.path == str(tmp_path)
    assert job.filename == "note.md"


def test_ingest_source_document_oversize_returns_413(client, usage_limits):
    conversation_id = uuid4()

    with (
        patch(
            "app.services.conversation.conversation_service.ConversationService.get_conversation",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "app.routes.ingest_routes.save_upload_to_temp",
            new=AsyncMock(
                side_effect=UploadTooLargeError(max_bytes=5 * 1024 * 1024, size=6_000_000)
            ),
        ),
        patch(
            "app.services.document.document_service.DocumentService.create_document",
            new=AsyncMock(),
        ) as create_document,
    ):
        response = client.post(
            f"/ingest/{conversation_id}/document",
            files={"file": ("note.md", b"# hello world", "text/markdown")},
        )

    assert response.status_code == 413
    payload = response.json()["detail"]
    assert payload["code"] == "max_upload_bytes"
    assert payload["current"] == 6_000_000
    create_document.assert_not_called()


def test_ingest_source_document_missing_conversation_returns_404(client):
    conversation_id = uuid4()

    with (
        patch(
            "app.services.conversation.conversation_service.ConversationService.get_conversation",
            new=AsyncMock(side_effect=ValueError("Conversation missing")),
        ),
        patch(
            "app.services.document.document_service.DocumentService.create_document",
            new=AsyncMock(),
        ) as create_document,
    ):
        response = client.post(
            f"/ingest/{conversation_id}/document",
            files={"file": ("note.md", b"# hello", "text/markdown")},
        )

    assert response.status_code == 404
    create_document.assert_not_called()


def test_ingest_source_url_missing_conversation_returns_404(client):
    conversation_id = uuid4()

    with (
        patch(
            "app.services.conversation.conversation_service.ConversationService.get_conversation",
            new=AsyncMock(side_effect=ValueError("Conversation missing")),
        ),
        patch(
            "app.services.document.document_service.DocumentService.create_document",
            new=AsyncMock(),
        ) as create_document,
    ):
        response = client.post(
            f"/ingest/{conversation_id}/url",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9wgXcQ"},
        )

    assert response.status_code == 404
    create_document.assert_not_called()


def test_ingest_note_resource_returns_202_and_enqueues_job(
    client,
    authenticated_user,
    ingest_queue,
    usage_limits,
):
    conversation_id = uuid4()
    resource = Resource(
        conversation_id=conversation_id,
        type=ResourceType.note,
        title="My Note",
        content={"kind": "user", "html": "<p>Hello</p>"},
    )
    document = Document(
        conversation_id=conversation_id,
        filename="My Note.md",
        content_type="text/markdown",
        status=DocumentStatus.pending,
    )
    tmp_path = Path("/tmp/fake-note-source.md")
    markdown = "# My Note\n\nHello\n"

    with (
        patch(
            "app.services.resource.resource_service.ResourceService.get_resource",
            new=AsyncMock(return_value=resource),
        ),
        patch(
            "app.services.document.document_service.DocumentService.create_document",
            new=AsyncMock(return_value=document),
        ) as create_document,
        patch(
            "app.services.document.document_service.DocumentService.mark_processing",
            new=_mark_processing(document),
        ),
        patch(
            "app.routes.ingest_routes.save_bytes_to_temp",
            return_value=(tmp_path, len(markdown.encode("utf-8"))),
        ) as save_bytes,
    ):
        response = client.post(
            f"/ingest/{conversation_id}/note/{resource.id}"
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["id"] == str(document.id)
    assert payload["status"] == "processing"
    assert payload["contentType"] == "text/markdown"
    assert payload["filename"] == "My Note.md"
    save_bytes.assert_called_once_with(
        markdown.encode("utf-8"),
        suffix=".md",
        max_bytes=usage_limits.settings.max_upload_bytes,
    )
    origin = create_document.await_args.kwargs["origin"]
    assert origin.kind == "file"
    ingest_queue.enqueue.assert_awaited_once()
    job = ingest_queue.enqueue.await_args.args[0]
    assert job.kind == "document"
    assert job.document_id == document.id
    assert job.user_id == authenticated_user.user_id
    assert job.path == str(tmp_path)
    assert job.filename == "My Note.md"


def test_ingest_note_resource_empty_returns_400(client):
    conversation_id = uuid4()
    resource = Resource(
        conversation_id=conversation_id,
        type=ResourceType.note,
        title="Empty",
        content={"kind": "user", "html": "<p></p>"},
    )

    with (
        patch(
            "app.services.resource.resource_service.ResourceService.get_resource",
            new=AsyncMock(return_value=resource),
        ),
        patch(
            "app.services.document.document_service.DocumentService.create_document",
            new=AsyncMock(),
        ) as create_document,
    ):
        response = client.post(
            f"/ingest/{conversation_id}/note/{resource.id}"
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Note has no content"
    create_document.assert_not_called()


def test_ingest_note_resource_not_found_returns_404(client):
    conversation_id = uuid4()
    resource_id = uuid4()

    with (
        patch(
            "app.services.resource.resource_service.ResourceService.get_resource",
            new=AsyncMock(side_effect=ValueError("Resource missing")),
        ),
        patch(
            "app.services.document.document_service.DocumentService.create_document",
            new=AsyncMock(),
        ) as create_document,
    ):
        response = client.post(
            f"/ingest/{conversation_id}/note/{resource_id}"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource missing"
    create_document.assert_not_called()
