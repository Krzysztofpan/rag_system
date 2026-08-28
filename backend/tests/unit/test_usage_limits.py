from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.config import Settings
from app.services.usage_limits import LimitCode, LimitExceededError, UsageLimitService


def test_limits_enabled_only_in_production():
    assert Settings(app_env="development").limits_enabled is False
    assert Settings(app_env="production").limits_enabled is True


def _settings(**overrides):
    values = dict(
        limits_enabled=True,
        max_upload_bytes=5 * 1024 * 1024,
        max_conversations=10,
        max_messages_per_conversation=20,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def _count_session(count: int) -> AsyncMock:
    result = MagicMock()
    result.scalar_one.return_value = count
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    return session


def _service(session, settings=None) -> UsageLimitService:
    return UsageLimitService(session, settings or _settings())


async def test_enforce_create_conversation_allows_under_limit():
    session = _count_session(9)
    await _service(session).enforce_create_conversation(uuid4())
    session.execute.assert_awaited_once()


async def test_enforce_create_conversation_rejects_at_limit():
    session = _count_session(10)
    with pytest.raises(LimitExceededError) as exc_info:
        await _service(session).enforce_create_conversation(uuid4())
    assert exc_info.value.code is LimitCode.max_conversations
    assert exc_info.value.status_code == 429
    assert exc_info.value.limit == 10
    assert exc_info.value.current == 10


async def test_enforce_conversation_messages_rejects_when_full():
    session = _count_session(20)
    with pytest.raises(LimitExceededError) as exc_info:
        await _service(session).enforce_conversation_messages(uuid4())
    assert exc_info.value.code is LimitCode.max_messages_per_conversation
    session.execute.assert_awaited_once()


async def test_enforce_skips_when_limits_are_disabled():
    session = _count_session(100)
    service = _service(session, _settings(limits_enabled=False))

    await service.enforce_create_conversation(uuid4())
    await service.enforce_conversation_messages(uuid4())

    session.execute.assert_not_called()


def test_upload_too_large_is_payload_too_large():
    service = _service(AsyncMock())
    with pytest.raises(LimitExceededError) as exc_info:
        service.raise_upload_too_large(size=5 * 1024 * 1024 + 1)
    assert exc_info.value.code is LimitCode.max_upload_bytes
    assert exc_info.value.status_code == 413
    assert exc_info.value.as_detail()["limit"] == 5 * 1024 * 1024
