"""API tests for authenticated conversation routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.auth.deps import AuthenticatedUser, get_current_user
from app.db.models.conversation import Conversation
from app.db.models.document import Document, DocumentStatus
from app.db.models.document_report import DocumentReport
from app.db.session import get_session
from app.routes.conversation_routes import conversation_router


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
        "app.routes.conversation_routes.ConversationStore.create_conversation",
        new=AsyncMock(return_value=conversation),
    ):
        response = client.post("/conversations/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversationId"] == str(conversation.id)
    assert payload["userId"] == str(authenticated_user.user_id)


def test_create_conversation_unknown_user_returns_400(client):
    with patch(
        "app.routes.conversation_routes.ConversationStore.create_conversation",
        new=AsyncMock(side_effect=IntegrityError("", {}, Exception())),
    ):
        response = client.post("/conversations/")

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown user"


def test_get_conversations_returns_store_result(client, authenticated_user):
    conversations = [
        Conversation(user_id=authenticated_user.user_id),
        Conversation(user_id=authenticated_user.user_id),
    ]

    with patch(
        "app.routes.conversation_routes.ConversationStore.get_conversations",
        new=AsyncMock(return_value=conversations),
    ):
        response = client.get("/conversations/")

    assert response.status_code == 200
    assert len(response.json()['conversations']) == 2


def test_get_sources_returns_documents(client, authenticated_user):
    conversation_id = uuid4()
    documents = [
        Document(
            conversation_id=conversation_id,
            filename="a.md",
            content_type="text/markdown",
            status=DocumentStatus.ready,
            chunk_count=3,
        )
    ]

    with patch(
        "app.routes.conversation_routes.ConversationStore.get_conversation_documents",
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
        "app.routes.conversation_routes.ConversationStore.get_conversation_documents",
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
        "app.routes.conversation_routes.DocumentStore.delete_document",
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
        "app.routes.conversation_routes.DocumentStore.change_document_name",
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
        "app.routes.conversation_routes.DocumentStore.get_report",
        new=AsyncMock(return_value=report),
    ):
        response = client.get(
            f"/conversations/{conversation_id}/sources/{document_id}/report"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["documentId"] == str(document_id)
    assert payload["parsedContent"] == "# Doc"
    assert payload["quality"]["parseReport"]["ok"] is True
