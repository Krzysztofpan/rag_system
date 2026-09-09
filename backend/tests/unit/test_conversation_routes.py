"""API tests for authenticated conversation routes."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.auth.deps import AuthenticatedUser, get_current_user
from app.container import (
    get_conversation_event_broker,
    get_usage_limit_service,
    get_vector_store,
)
from app.db.models.conversation import Conversation
from app.db.models.document import Document, DocumentStatus
from app.db.models.document_report import DocumentReport
from app.db.models.message import Message, MessageRole
from app.db.session import get_session
from app.lib.exceptions import register_limit_exceeded_handler
from app.lib.rate_limit import configure_rate_limiting, limiter
from app.routes.conversation_routes import conversation_router
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
def usage_limits():
    service = AsyncMock()
    service.enabled = True
    service.settings.max_upload_bytes = 5 * 1024 * 1024
    return service


@pytest.fixture
def client(authenticated_user, mock_session, usage_limits):
    limiter.reset()
    app = FastAPI()
    configure_rate_limiting(app)
    register_limit_exceeded_handler(app)
    app.include_router(conversation_router)

    async def override_session():
        yield mock_session

    app.dependency_overrides[get_current_user] = override_authenticated_user(
        authenticated_user
    )
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_vector_store] = lambda: FakeVectorStore()
    app.dependency_overrides[get_usage_limit_service] = lambda: usage_limits
    app.dependency_overrides[get_conversation_event_broker] = lambda: AsyncMock()

    with TestClient(app) as test_client:
        yield test_client


def test_conversation_routes_require_authentication():
    app = FastAPI()
    app.include_router(conversation_router)

    with TestClient(app) as test_client:
        response = test_client.post("/conversations/")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_create_conversation_returns_ids(client, authenticated_user, usage_limits):
    conversation = Conversation(user_id=authenticated_user.user_id)

    with patch(
        "app.services.conversation.conversation_service.ConversationService.create_conversation",
        new=AsyncMock(return_value=conversation),
    ):
        response = client.post("/conversations/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversationId"] == str(conversation.id)
    assert payload["userId"] == str(authenticated_user.user_id)
    usage_limits.enforce_create_conversation.assert_awaited_once_with(
        authenticated_user.user_id
    )


def test_create_conversation_limit_returns_429(client, usage_limits):
    usage_limits.enforce_create_conversation.side_effect = LimitExceededError(
        LimitCode.max_conversations,
        limit=10,
        current=10,
        message="Conversation limit reached (10).",
    )

    response = client.post("/conversations/")

    assert response.status_code == 429
    payload = response.json()["detail"]
    assert payload["code"] == "max_conversations"
    assert payload["limit"] == 10
    assert payload["current"] == 10


def test_create_conversation_unknown_user_returns_400(client):
    with patch(
        "app.services.conversation.conversation_service.ConversationService.create_conversation",
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
        "app.services.conversation.conversation_service.ConversationService.get_conversations",
        new=AsyncMock(return_value=conversations),
    ):
        response = client.get("/conversations/")

    assert response.status_code == 200
    assert len(response.json()['conversations']) == 2


def test_get_conversation_returns_serialized_conversation(client, authenticated_user):
    conversation = Conversation(user_id=authenticated_user.user_id, title="My chat", topic="ai")

    with patch(
        "app.services.conversation.conversation_service.ConversationService.get_conversation",
        new=AsyncMock(return_value=conversation),
    ):
        response = client.get(f"/conversations/{conversation.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(conversation.id)
    assert payload["userId"] == str(authenticated_user.user_id)
    assert payload["title"] == "My chat"
    assert payload["topic"] == "ai"
    assert payload["sourceCount"] == 0
    assert payload["documentsSummary"] is None
    assert "createdAt" in payload
    assert "updatedAt" in payload


def test_get_conversation_includes_documents_summary(client, authenticated_user):
    conversation = Conversation(
        user_id=authenticated_user.user_id,
        title="Go notes",
        topic="tech",
    )
    conversation.__dict__["summary_state"] = SimpleNamespace(
        documents_summary="A video about Go 1.27.",
    )

    with patch(
        "app.services.conversation.conversation_service.ConversationService.get_conversation",
        new=AsyncMock(return_value=conversation),
    ):
        response = client.get(f"/conversations/{conversation.id}")

    assert response.status_code == 200
    assert response.json()["documentsSummary"] == "A video about Go 1.27."


def test_get_conversation_not_found_returns_404(client):
    conversation_id = uuid4()

    with patch(
        "app.services.conversation.conversation_service.ConversationService.get_conversation",
        new=AsyncMock(side_effect=ValueError(f"Conversation {conversation_id} not found")),
    ):
        response = client.get(f"/conversations/{conversation_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == f"Conversation {conversation_id} not found"


def test_get_conversation_requires_authentication():
    conversation_id = uuid4()
    app = FastAPI()
    app.include_router(conversation_router)

    with TestClient(app) as test_client:
        response = test_client.get(f"/conversations/{conversation_id}")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_conversation_events_requires_authentication():
    conversation_id = uuid4()
    app = FastAPI()
    app.include_router(conversation_router)

    with TestClient(app) as test_client:
        response = test_client.get(f"/conversations/{conversation_id}/events")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_conversation_events_not_found_returns_404(client):
    conversation_id = uuid4()

    with patch(
        "app.services.conversation.conversation_service.ConversationService.get_conversation",
        new=AsyncMock(side_effect=ValueError(f"Conversation {conversation_id} not found")),
    ):
        response = client.get(f"/conversations/{conversation_id}/events")

    assert response.status_code == 404
    assert response.json()["detail"] == f"Conversation {conversation_id} not found"


def test_get_messages_serializes_sources_with_api_aliases(client):
    conversation_id = uuid4()
    chunk_id = uuid4()
    message = Message(
        conversation_id=conversation_id,
        text="Answer [1]",
        role=MessageRole.assistant,
        sources=[
            {"index": 1, "kind": "chunk", "chunk_id": str(chunk_id)},
        ],
    )
    page = SimpleNamespace(messages=[message], has_more=False)

    with (
        patch(
            "app.services.conversation.conversation_service.ConversationService.get_conversation",
            new=AsyncMock(return_value=SimpleNamespace(id=conversation_id)),
        ),
        patch(
            "app.services.conversation.message_service.MessageService.get_messages",
            new=AsyncMock(return_value=page),
        ),
    ):
        response = client.get(f"/conversations/{conversation_id}/messages")

    assert response.status_code == 200
    payload = response.json()
    assert payload["messages"][0]["sources"] == [
        {"index": 1, "kind": "chunk", "chunkId": str(chunk_id)},
    ]


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
        "app.services.document.document_service.DocumentService.get_conversation_documents",
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
        "app.services.document.document_service.DocumentService.get_conversation_documents",
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
        "app.services.document.document_service.DocumentService.delete_document",
        new=AsyncMock(return_value=document),
    ), patch(
        "app.routes.conversation_routes.refresh_and_publish_documents_summary",
        new=AsyncMock(),
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
        "app.services.document.document_service.DocumentService.change_document_name",
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
        "app.services.document.document_service.DocumentService.get_report",
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


def test_get_chunk_returns_payload(client):
    conversation_id = uuid4()
    chunk_id = uuid4()
    document_id = uuid4()
    chunk = SimpleNamespace(
        id=chunk_id,
        content="Pracownik nie musi informować o L4.",
        pages=[4],
        chunk_index=2,
    )
    document = SimpleNamespace(id=document_id, filename="regulamin.pdf")

    with patch(
        "app.services.document.document_service.DocumentService.get_chunk",
        new=AsyncMock(return_value=(chunk, document)),
    ):
        response = client.get(
            f"/conversations/{conversation_id}/chunks/{chunk_id}"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(chunk_id)
    assert payload["documentId"] == str(document_id)
    assert payload["filename"] == "regulamin.pdf"
    assert payload["content"] == "Pracownik nie musi informować o L4."
    assert payload["pages"] == [4]
    assert payload["chunkIndex"] == 2


def test_get_chunk_not_found_returns_404(client):
    conversation_id = uuid4()
    chunk_id = uuid4()

    with patch(
        "app.services.document.document_service.DocumentService.get_chunk",
        new=AsyncMock(side_effect=ValueError("Chunk not found")),
    ):
        response = client.get(
            f"/conversations/{conversation_id}/chunks/{chunk_id}"
        )

    assert response.status_code == 404


def test_delete_conversation_returns_deleted_conversation(client, authenticated_user):
    conversation = Conversation(user_id=authenticated_user.user_id)

    with patch(
        "app.services.conversation.conversation_service.ConversationService.delete_conversation",
        new=AsyncMock(return_value=conversation),
    ):
        response = client.delete(f"/conversations/{conversation.id}")

    assert response.status_code == 200
    assert response.json()["deletedConversation"]["id"] == str(conversation.id)
