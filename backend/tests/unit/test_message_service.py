from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.models.message import Message, MessageRole
from app.services.message_service import MessageService


def _result_with_messages(messages):
    result = MagicMock()
    result.scalars.return_value.all.return_value = messages
    return result


async def test_get_messages_after_returns_recent_messages_chronologically():
    conversation_id = uuid4()
    older = Message(
        conversation_id=conversation_id,
        role=MessageRole.user,
        text="older",
    )
    newer = Message(
        conversation_id=conversation_id,
        role=MessageRole.assistant,
        text="newer",
    )
    session = AsyncMock()
    session.execute.return_value = _result_with_messages([newer, older])

    messages = await MessageService(session).get_messages_after(
        conversation_id,
        user_id=uuid4(),
        after_id=None,
        limit=2,
        newest_first=True,
    )

    assert messages == [older, newer]


async def test_get_messages_after_rejects_unknown_watermark():
    cursor_result = MagicMock()
    cursor_result.one_or_none.return_value = None
    session = AsyncMock()
    session.execute.return_value = cursor_result

    with pytest.raises(ValueError, match="not found"):
        await MessageService(session).get_messages_after(
            uuid4(),
            user_id=uuid4(),
            after_id=uuid4(),
            limit=10,
        )
