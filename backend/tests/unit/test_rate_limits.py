from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from limits.storage import MemoryStorage

from app.auth.deps import AuthenticatedUser, get_current_user
from app.config import Settings
from app.container import (
    get_conversation_memory_service,
    get_ingest_queue,
    get_run_registry,
    get_usage_limit_service,
    get_vector_store,
)
from app.db.models.document import Document, DocumentStatus
from app.db.session import get_session
from app.lib.rate_limit import (
    bind_limiter_storage,
    configure_rate_limiting,
    limiter,
)
from app.routes.chat_stream_routes import chat_stream_router
from app.routes.conversation_routes import conversation_router
from app.services.security.prompt_guard import get_prompt_guard_service
from tests.helpers import FakeVectorStore, override_authenticated_user


def test_rate_limit_storage_defaults_to_redis_url():
    settings = Settings(
        redis_host="redis",
        redis_port=6379,
        redis_url=None,
        rate_limit_storage_uri=None,
    )
    assert settings.resolved_rate_limit_storage_uri == "redis://redis:6379"


def test_rate_limit_storage_explicit_uri_wins():
    settings = Settings(
        redis_host="redis",
        redis_port=6379,
        redis_url=None,
        rate_limit_storage_uri="memory://",
    )
    assert settings.resolved_rate_limit_storage_uri == "memory://"


def test_rate_limit_storage_falls_back_to_memory_without_redis():
    settings = Settings(redis_host=None, redis_url=None, rate_limit_storage_uri=None)
    assert settings.resolved_rate_limit_storage_uri == "memory://"


def test_rate_limit_strategy_defaults_to_fixed_window():
    assert Settings().rate_limit_strategy == "fixed-window"


def test_configure_rate_limiting_binds_redis_storage(monkeypatch):
    seen: list[str] = []

    def fake_storage_from_string(uri: str, **_kwargs):
        seen.append(uri)
        return MemoryStorage()

    monkeypatch.setattr(
        "app.lib.rate_limit.storage_from_string",
        fake_storage_from_string,
    )
    settings = Settings(
        app_env="production",
        redis_host="redis",
        redis_port=6379,
        redis_url=None,
        rate_limit_storage_uri=None,
    )
    app = FastAPI()
    try:
        configure_rate_limiting(app, settings)
        assert seen == ["redis://redis:6379"]
        assert limiter._storage_uri == "redis://redis:6379"
        assert limiter._strategy == "fixed-window"
        assert app.state.limiter is limiter
        assert limiter.enabled is True
    finally:
        bind_limiter_storage("memory://")
        limiter.reset()
        limiter.enabled = False


@pytest.fixture
def authenticated_user():
    return AuthenticatedUser(
        access_token="test-token",
        user_id=uuid4(),
        email="user@example.com",
        role="authenticated",
        phone=None,
        app_metadata={},
        user_metadata={},
    )


def _client(authenticated_user) -> TestClient:
    limiter.reset()
    app = FastAPI()
    configure_rate_limiting(app)
    limiter.enabled = True
    app.include_router(conversation_router)
    app.include_router(chat_stream_router)

    async def override_session():
        yield AsyncMock()

    guard = MagicMock()
    guard.should_block_message = AsyncMock(return_value=False)
    registry = AsyncMock()
    registry.start.side_effect = RuntimeError("busy")

    app.dependency_overrides[get_current_user] = override_authenticated_user(
        authenticated_user
    )
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_vector_store] = lambda: FakeVectorStore()
    app.dependency_overrides[get_usage_limit_service] = lambda: AsyncMock(
        settings=MagicMock(max_upload_bytes=5 * 1024 * 1024)
    )
    app.dependency_overrides[get_prompt_guard_service] = lambda: guard
    app.dependency_overrides[get_run_registry] = lambda: registry
    app.dependency_overrides[get_conversation_memory_service] = lambda: AsyncMock()
    app.dependency_overrides[get_ingest_queue] = lambda: AsyncMock()
    return TestClient(app)


def test_ingest_endpoints_share_daily_quota(authenticated_user):
    conversation_id = uuid4()
    document = Document(
        conversation_id=conversation_id,
        filename="youtube:dQw4w9wgXcQ",
        content_type="video/youtube",
        status=DocumentStatus.pending,
    )

    async def mark_processing(_document_id):
        document.status = DocumentStatus.processing
        return document

    client = _client(authenticated_user)
    with (
        patch(
            "app.services.conversation_service.ConversationService.get_conversation",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "app.services.document_service.DocumentService.create_document",
            new=AsyncMock(return_value=document),
        ),
        patch(
            "app.services.document_service.DocumentService.mark_processing",
            new=AsyncMock(side_effect=mark_processing),
        ),
        patch(
            "app.routes.conversation_routes.save_upload_to_temp",
            new=AsyncMock(return_value=(Path("/tmp/note.md"), 12)),
        ),
    ):
        url = f"/conversations/{conversation_id}/sources/url"
        payload = {"url": "https://www.youtube.com/watch?v=dQw4w9wgXcQ"}
        assert client.post(url, json=payload).status_code == 202
        assert client.post(url, json=payload).status_code == 202
        file_response = client.post(
            f"/conversations/{conversation_id}/sources/document",
            files={"file": ("note.md", b"# hello", "text/markdown")},
        )
        assert file_response.status_code == 202
        blocked = client.post(url, json=payload)

    assert blocked.status_code == 429
    detail = blocked.json()["detail"]
    assert detail["code"] == "max_ingests_per_day"
    assert detail["limit"] == 3
    assert blocked.headers["retry-after"]


def test_chat_commands_daily_message_limit_returns_429(authenticated_user):
    conversation_id = uuid4()
    client = _client(authenticated_user)
    body = {
        "id": 1,
        "method": "run.start",
        "params": {
            "input": {
                "messages": [
                    {
                        "id": str(uuid4()),
                        "type": "human",
                        "content": "Hello",
                    }
                ],
                "documentIds": [],
            }
        },
    }

    with patch(
        "app.services.conversation_service.ConversationService.get_conversation",
        new=AsyncMock(return_value=MagicMock()),
    ):
        for _ in range(20):
            response = client.post(
                f"/conversations/{conversation_id}/commands",
                json=body,
            )
            assert response.status_code == 200
        blocked = client.post(
            f"/conversations/{conversation_id}/commands",
            json=body,
        )

    assert blocked.status_code == 429
    detail = blocked.json()["detail"]
    assert detail["code"] == "max_messages_per_day"
    assert detail["limit"] == 20
    assert blocked.headers["retry-after"]


def test_daily_limits_are_not_enforced_when_disabled(authenticated_user):
    conversation_id = uuid4()
    document = Document(
        conversation_id=conversation_id,
        filename="youtube:dQw4w9wgXcQ",
        content_type="video/youtube",
        status=DocumentStatus.pending,
    )

    async def mark_processing(_document_id):
        document.status = DocumentStatus.processing
        return document

    limiter.reset()
    app = FastAPI()
    configure_rate_limiting(app)
    limiter.enabled = False
    app.include_router(conversation_router)

    async def override_session():
        yield AsyncMock()

    app.dependency_overrides[get_current_user] = override_authenticated_user(
        authenticated_user
    )
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_vector_store] = lambda: FakeVectorStore()
    app.dependency_overrides[get_usage_limit_service] = lambda: AsyncMock(
        settings=MagicMock(max_upload_bytes=5 * 1024 * 1024)
    )
    app.dependency_overrides[get_ingest_queue] = lambda: AsyncMock()
    client = TestClient(app)

    with (
        patch(
            "app.services.conversation_service.ConversationService.get_conversation",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "app.services.document_service.DocumentService.create_document",
            new=AsyncMock(return_value=document),
        ),
        patch(
            "app.services.document_service.DocumentService.mark_processing",
            new=AsyncMock(side_effect=mark_processing),
        ),
    ):
        url = f"/conversations/{conversation_id}/sources/url"
        payload = {"url": "https://www.youtube.com/watch?v=dQw4w9wgXcQ"}
        statuses = [
            client.post(url, json=payload).status_code for _ in range(4)
        ]

    assert statuses == [202, 202, 202, 202]
