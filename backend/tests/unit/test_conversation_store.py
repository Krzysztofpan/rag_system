"""Unit tests for ConversationStore user-scoped lookups."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.models.conversation import Conversation
from app.db.models.document import Document, DocumentStatus
from app.services.conversation_store import ConversationStore


def _mock_session(*, scalar_one_or_none=None, scalars_all=None) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_one_or_none
    scalars = MagicMock()
    scalars.all.return_value = scalars_all or []
    result.scalars.return_value = scalars
    session.execute = AsyncMock(return_value=result)
    return session


async def test_create_conversation_persists_and_refreshes():
    user_id = uuid4()
    session = AsyncMock()
    session.add = MagicMock()
    store = ConversationStore(session)

    conversation = await store.create_conversation(user_id=user_id)

    assert isinstance(conversation, Conversation)
    assert conversation.user_id == user_id
    session.add.assert_called_once_with(conversation)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(conversation)


async def test_get_conversations_returns_user_rows():
    user_id = uuid4()
    conversations = [Conversation(user_id=user_id), Conversation(user_id=user_id)]
    session = _mock_session(scalars_all=conversations)
    store = ConversationStore(session)

    result = await store.get_conversations(user_id=user_id)

    assert result == conversations
    session.execute.assert_awaited_once()


async def test_get_conversation_returns_owned_conversation():
    user_id = uuid4()
    conversation = Conversation(user_id=user_id)
    session = _mock_session(scalar_one_or_none=conversation)
    store = ConversationStore(session)

    result = await store.get_conversation(conversation.id, user_id=user_id)

    assert result is conversation


async def test_get_conversation_raises_when_missing_or_foreign():
    conversation_id = uuid4()
    session = _mock_session(scalar_one_or_none=None)
    store = ConversationStore(session)

    with pytest.raises(ValueError, match=f"Conversation {conversation_id} not found"):
        await store.get_conversation(conversation_id, user_id=uuid4())


async def test_get_conversation_documents_requires_ownership():
    user_id = uuid4()
    conversation = Conversation(user_id=user_id)
    documents = [
        Document(
            conversation_id=conversation.id,
            filename="a.md",
            status=DocumentStatus.ready,
        )
    ]
    session = AsyncMock()
    ownership_result = MagicMock()
    ownership_result.scalar_one_or_none.return_value = conversation
    documents_result = MagicMock()
    documents_result.scalars.return_value.all.return_value = documents
    session.execute = AsyncMock(side_effect=[ownership_result, documents_result])
    store = ConversationStore(session)

    result = await store.get_conversation_documents(
        conversation.id,
        user_id=user_id,
    )

    assert result == documents
    assert session.execute.await_count == 2
