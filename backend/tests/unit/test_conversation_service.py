"""Unit tests for ConversationService user-scoped lookups."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.db.models.conversation import Conversation
from app.services.conversation_service import ConversationMetadata, ConversationService
from tests.helpers import FakeVectorStore


def _service(session, vector_store=None) -> ConversationService:
    return ConversationService(
        session,
        vector_store or FakeVectorStore(),
    )


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
    service = _service(session)

    conversation = await service.create_conversation(user_id=user_id)

    assert isinstance(conversation, Conversation)
    assert conversation.user_id == user_id
    session.add.assert_called_once_with(conversation)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(conversation)


async def test_get_conversations_returns_user_rows():
    user_id = uuid4()
    conversations = [Conversation(user_id=user_id), Conversation(user_id=user_id)]
    session = _mock_session(scalars_all=conversations)
    service = _service(session)

    result = await service.get_conversations(user_id=user_id)

    assert result == conversations
    session.execute.assert_awaited_once()


async def test_get_conversation_returns_owned_conversation():
    user_id = uuid4()
    conversation = Conversation(user_id=user_id)
    session = _mock_session(scalar_one_or_none=conversation)
    service = _service(session)

    result = await service.get_conversation(conversation.id, user_id=user_id)

    assert result is conversation


async def test_get_conversation_raises_when_missing_or_foreign():
    conversation_id = uuid4()
    session = _mock_session(scalar_one_or_none=None)
    service = _service(session)

    with pytest.raises(ValueError, match=f"Conversation {conversation_id} not found"):
        await service.get_conversation(conversation_id, user_id=uuid4())


async def test_delete_conversation_removes_sql_row_then_namespace():
    user_id = uuid4()
    conversation = Conversation(user_id=user_id)
    session = _mock_session(scalar_one_or_none=conversation)
    vector_store = FakeVectorStore()
    service = _service(session, vector_store)

    result = await service.delete_conversation(conversation.id, user_id=user_id)

    assert result is conversation
    session.delete.assert_awaited_once_with(conversation)
    session.commit.assert_awaited_once()
    assert vector_store.deleted_namespaces == [conversation.id]


async def test_delete_conversation_succeeds_when_pinecone_fails():
    user_id = uuid4()
    conversation = Conversation(user_id=user_id)
    session = _mock_session(scalar_one_or_none=conversation)
    vector_store = MagicMock()
    vector_store.delete_namespace.side_effect = RuntimeError("pinecone down")
    service = _service(session, vector_store)

    result = await service.delete_conversation(conversation.id, user_id=user_id)

    assert result is conversation
    session.commit.assert_awaited_once()
    vector_store.delete_namespace.assert_called_once_with(conversation.id)


async def test_delete_conversation_skips_pinecone_when_missing():
    conversation_id = uuid4()
    session = _mock_session(scalar_one_or_none=None)
    vector_store = FakeVectorStore()
    service = _service(session, vector_store)

    with pytest.raises(ValueError, match=f"Conversation {conversation_id} not found"):
        await service.delete_conversation(conversation_id, user_id=uuid4())

    session.delete.assert_not_called()
    assert vector_store.deleted_namespaces == []


async def test_update_from_summary_updates_title_and_topic():
    user_id = uuid4()
    conversation = Conversation(user_id=user_id, title="New Conversation")
    session = _mock_session(scalar_one_or_none=conversation)
    service = _service(session)

    chain = MagicMock()
    chain.__or__.return_value = chain
    chain.ainvoke = AsyncMock(
        return_value=ConversationMetadata(title="Contracts and invoices", topic="finance")
    )

    with (
        patch(
            "app.services.conversation_service.ChatPromptTemplate.from_template",
            return_value=chain,
        ),
        patch("app.services.conversation_service.ChatOpenAI"),
    ):
        title, topic = await service.update_from_summary(
            conversation.id,
            "A summary of invoices",
            user_id=user_id,
        )

    chain.ainvoke.assert_awaited_once_with(
        {
            "doc_summary": "A summary of invoices",
            "conversation_title": "New Conversation",
        },
        config={"run_name": "generate_conversation_metadata"},
    )
    assert title == "Contracts and invoices"
    assert topic == "finance"
    assert conversation.title == "Contracts and invoices"
    assert conversation.topic == "finance"
    session.commit.assert_awaited_once()
