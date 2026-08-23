"""API tests for authenticated conversation routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.auth.deps import AuthenticatedUser, get_current_user
from app.container import get_vector_store
from app.db.models.conversation import Conversation
from app.db.models.document import Document, DocumentStatus
from app.db.models.document_report import DocumentReport
from app.db.session import get_session
from app.routes.conversation_routes import conversation_router
from tests.helpers import FakeVectorStore


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
def client(authenticated_user, mock_session):
    app = FastAPI()
    app.include_router(conversation_router)

    async def override_session():
        yield mock_session

    app.dependency_overrides[get_current_user] = lambda: authenticated_user
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_vector_store] = lambda: FakeVectorStore()

    with TestClient(app) as test_client:
        yield test_client


def test_conversation_routes_require_authentication():
    app = FastAPI()
    app.include_router(conversation_router)

    with TestClient(app) as test_client:
        response = test_client.post("/conversations/")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_create_conversation_returns_ids(client, authenticated_user):
    conversation = Conversation(user_id=authenticated_user.user_id)

    with patch(
        "app.services.conversation_service.ConversationService.create_conversation",
        new=AsyncMock(return_value=conversation),
    ):
        response = client.post("/conversations/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversationId"] == str(conversation.id)
    assert payload["userId"] == str(authenticated_user.user_id)


def test_create_conversation_unknown_user_returns_400(client):
    with patch(
        "app.services.conversation_service.ConversationService.create_conversation",
        new=AsyncMock(side_effect=IntegrityError("", {}, Exception())),
    ):
        response = client.post("/conversations/")

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown user"


def test_get_conversations_returns_service_result(client, authenticated_user):
    conversations = [
        Conversation(user_id=authenticated_user.user_id),
        Conversation(user_id=authenticated_user.user_id),
    ]

    with patch(
        "app.services.conversation_service.ConversationService.get_conversations",
        new=AsyncMock(return_value=conversations),
    ):
        response = client.get("/conversations/")

    assert response.status_code == 200
    assert len(response.json()['conversations']) == 2


def test_ingest_source_url_rejects_invalid_url_without_creating_document(client):
    conversation_id = uuid4()

    with patch(
        "app.services.document_service.DocumentService.create_document",
        new=AsyncMock(),
    ) as create_document:
        response = client.post(
            f"/conversations/{conversation_id}/sources/url",
            json={"url": "https://example.com/watch?v=dQw4w9wgXcQ"},
        )

    assert response.status_code == 400
    create_document.assert_not_called()


def test_ingest_source_url_returns_202_and_queues_background(
    client,
    authenticated_user,
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
            "app.services.conversation_service.ConversationService.get_conversation",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "app.services.document_service.DocumentService.create_document",
            new=AsyncMock(return_value=document),
        ) as create_document,
        patch(
            "app.services.document_service.DocumentService.mark_processing",
            new=_mark_processing(document),
        ),
        patch(
            "app.routes.conversation_routes.ingest_youtube_source",
            new=AsyncMock(),
        ) as background,
    ):
        response = client.post(
            f"/conversations/{conversation_id}/sources/url",
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
    background.assert_awaited_once()
    assert background.await_args.args[1] == document.id
    assert background.await_args.args[2] == authenticated_user.user_id
    assert background.await_args.args[4] == "dQw4w9wgXcQ"


def test_ingest_source_document_rejects_unsupported_type_without_creating_document(client):
    conversation_id = uuid4()

    with patch(
        "app.services.document_service.DocumentService.create_document",
        new=AsyncMock(),
    ) as create_document:
        response = client.post(
            f"/conversations/{conversation_id}/sources/document",
            files={"file": ("archive.zip", b"PK", "application/zip")},
        )

    assert response.status_code == 400
    create_document.assert_not_called()


def test_ingest_source_document_returns_202_and_queues_background(
    client,
    authenticated_user,
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
            "app.services.conversation_service.ConversationService.get_conversation",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "app.services.document_service.DocumentService.create_document",
            new=AsyncMock(return_value=document),
        ) as create_document,
        patch(
            "app.services.document_service.DocumentService.mark_processing",
            new=_mark_processing(document),
        ),
        patch(
            "app.routes.conversation_routes.save_upload_to_temp",
            new=AsyncMock(return_value=(tmp_path, 12)),
        ),
        patch(
            "app.routes.conversation_routes.ingest_document_source",
            new=AsyncMock(),
        ) as background,
    ):
        response = client.post(
            f"/conversations/{conversation_id}/sources/document",
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
    background.assert_awaited_once()
    assert background.await_args.args[1] == document.id
    assert background.await_args.args[2] == authenticated_user.user_id
    assert background.await_args.args[3] == str(tmp_path)
    assert background.await_args.args[4] == "note.md"


def test_ingest_source_document_missing_conversation_returns_404(client):
    conversation_id = uuid4()

    with (
        patch(
            "app.services.conversation_service.ConversationService.get_conversation",
            new=AsyncMock(side_effect=ValueError("Conversation missing")),
        ),
        patch(
            "app.services.document_service.DocumentService.create_document",
            new=AsyncMock(),
        ) as create_document,
    ):
        response = client.post(
            f"/conversations/{conversation_id}/sources/document",
            files={"file": ("note.md", b"# hello", "text/markdown")},
        )

    assert response.status_code == 404
    create_document.assert_not_called()


def test_ingest_source_url_missing_conversation_returns_404(client):
    conversation_id = uuid4()

    with (
        patch(
            "app.services.conversation_service.ConversationService.get_conversation",
            new=AsyncMock(side_effect=ValueError("Conversation missing")),
        ),
        patch(
            "app.services.document_service.DocumentService.create_document",
            new=AsyncMock(),
        ) as create_document,
    ):
        response = client.post(
            f"/conversations/{conversation_id}/sources/url",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9wgXcQ"},
        )

    assert response.status_code == 404
    create_document.assert_not_called()


def test_get_sources_returns_documents(client, authenticated_user):
    conversation_id = uuid4()
    documents = [
        Document(
            conversation_id=conversation_id,
            filename="a.md",
            content_type="text/markdown",
            status=DocumentStatus.ready,
        )
    ]

    with patch(
        "app.services.document_service.DocumentService.get_conversation_documents",
        new=AsyncMock(return_value=documents),
    ):
        response = client.get(f"/conversations/{conversation_id}/sources")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["conversationSources"][0]["filename"] == "a.md"
    assert payload["conversationSources"][0]["status"] == "ready"


def test_get_sources_not_found_returns_404(client):
    conversation_id = uuid4()

    with patch(
        "app.services.document_service.DocumentService.get_conversation_documents",
        new=AsyncMock(side_effect=ValueError("Conversation missing")),
    ):
        response = client.get(f"/conversations/{conversation_id}/sources")

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation missing"


def test_delete_source_returns_deleted_document(client):
    conversation_id = uuid4()
    document = Document(
        conversation_id=conversation_id,
        filename="note.md",
        status=DocumentStatus.ready,
    )

    with patch(
        "app.services.document_service.DocumentService.delete_document",
        new=AsyncMock(return_value=document),
    ):
        response = client.delete(
            f"/conversations/{conversation_id}/sources/{document.id}"
        )

    assert response.status_code == 200
    assert response.json()["deletedDocument"]["filename"] == "note.md"


def test_change_source_name_returns_updated_name(client):
    conversation_id = uuid4()
    document_id = uuid4()

    with patch(
        "app.services.document_service.DocumentService.change_document_name",
        new=AsyncMock(return_value="renamed.md"),
    ):
        response = client.patch(
            f"/conversations/{conversation_id}/sources/{document_id}",
            json="renamed.md",
        )

    assert response.status_code == 200
    assert response.json() == "renamed.md"


def test_get_source_report_returns_report_payload(client):
    conversation_id = uuid4()
    document_id = uuid4()
    report = DocumentReport(
        document_id=document_id,
        parsed_content="# Doc",
        summary="Doc overview",
        quality={
            "parse_report": {"ok": True, "counts": {}, "issues": []},
            "chunk_quality": {
                "ok": True,
                "total_chunks": 1,
                "kept_chunks": 1,
                "rejected_chunks": 0,
                "rejected_ratio": 0.0,
                "max_rejected_ratio": 0.25,
                "rejected": [],
            },
        },
    )

    with patch(
        "app.services.document_service.DocumentService.get_report",
        new=AsyncMock(return_value=report),
    ):
        response = client.get(
            f"/conversations/{conversation_id}/sources/{document_id}/report"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["documentId"] == str(document_id)
    assert payload["parsedContent"] == "# Doc"
    assert payload["summary"] == "Doc overview"
    assert payload["quality"]["parseReport"]["ok"] is True


def test_delete_conversation_returns_deleted_conversation(client, authenticated_user):
    conversation = Conversation(user_id=authenticated_user.user_id)

    with patch(
        "app.services.conversation_service.ConversationService.delete_conversation",
        new=AsyncMock(return_value=conversation),
    ):
        response = client.delete(f"/conversations/{conversation.id}")

    assert response.status_code == 200
    assert response.json()["deletedConversation"]["id"] == str(conversation.id)
