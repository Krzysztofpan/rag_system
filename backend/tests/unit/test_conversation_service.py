"""Unit tests for ConversationService user-scoped lookups."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.models.conversation import Conversation
from app.db.models.document import Document, DocumentStatus
from app.services.conversation_service import ConversationService
from tests.helpers import FakeDocumentStore, FakeVectorStore


def _service(session, vector_store=None, doc_store=None) -> ConversationService:
    return ConversationService(
        session,
        vector_store or FakeVectorStore(),
        doc_store or FakeDocumentStore(),
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
    service = _service(session)

    result = await service.get_conversation_documents(
        conversation.id,
        user_id=user_id,
    )

    assert result == documents
    assert session.execute.await_count == 2


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


async def test_delete_document_removes_sql_then_vectors(
    conversation_id,
    fake_doc_store,
    fake_vector_store,
):
    document = await fake_doc_store.create_document(
        conversation_id=conversation_id,
        filename="note.md",
    )
    service = _service(AsyncMock(), fake_vector_store, fake_doc_store)

    deleted = await service.delete_document(
        conversation_id,
        document.id,
        user_id=uuid4(),
    )

    assert deleted.id == document.id
    assert document.id not in fake_doc_store.documents
    assert fake_vector_store.deleted_documents == [(conversation_id, document.id)]
    assert fake_vector_store.deleted_namespaces == []


async def test_delete_document_succeeds_when_pinecone_fails(
    conversation_id,
    fake_doc_store,
):
    document = await fake_doc_store.create_document(
        conversation_id=conversation_id,
        filename="note.md",
    )
    vector_store = FakeVectorStore()
    vector_store.delete_document_vectors = MagicMock(
        side_effect=RuntimeError("pinecone down")
    )
    service = _service(AsyncMock(), vector_store, fake_doc_store)

    deleted = await service.delete_document(
        conversation_id,
        document.id,
        user_id=uuid4(),
    )

    assert deleted.id == document.id
    assert document.id not in fake_doc_store.documents


async def test_delete_document_skips_pinecone_when_sql_fails(
    conversation_id,
    fake_vector_store,
):
    doc_store = MagicMock()
    doc_store.delete_document = AsyncMock(
        side_effect=ValueError("Document not found in conversation")
    )
    service = _service(AsyncMock(), fake_vector_store, doc_store)

    with pytest.raises(ValueError, match="Document not found"):
        await service.delete_document(conversation_id, uuid4(), user_id=uuid4())

    assert fake_vector_store.deleted_documents == []


async def test_change_document_name_updates_sql_then_vector_metadata(
    conversation_id,
    fake_doc_store,
    fake_vector_store,
):
    document = await fake_doc_store.create_document(
        conversation_id=conversation_id,
        filename="note.md",
    )
    service = _service(AsyncMock(), fake_vector_store, fake_doc_store)

    updated = await service.change_document_name(
        conversation_id,
        document.id,
        "renamed.md",
        user_id=uuid4(),
    )

    assert updated == "renamed.md"
    assert document.filename == "renamed.md"
    assert fake_vector_store.updated_source_filenames == [
        (conversation_id, document.id, "renamed.md")
    ]


async def test_change_document_name_succeeds_when_pinecone_fails(
    conversation_id,
    fake_doc_store,
):
    document = await fake_doc_store.create_document(
        conversation_id=conversation_id,
        filename="note.md",
    )
    vector_store = FakeVectorStore()
    vector_store.update_document_source_filename = MagicMock(
        side_effect=RuntimeError("pinecone down")
    )
    service = _service(AsyncMock(), vector_store, fake_doc_store)

    updated = await service.change_document_name(
        conversation_id,
        document.id,
        "renamed.md",
        user_id=uuid4(),
    )

    assert updated == "renamed.md"
    assert document.filename == "renamed.md"


async def test_change_document_name_skips_pinecone_when_sql_fails(
    conversation_id,
    fake_vector_store,
):
    doc_store = MagicMock()
    doc_store.change_document_name = AsyncMock(
        side_effect=ValueError("Document not found in conversation")
    )
    service = _service(AsyncMock(), fake_vector_store, doc_store)

    with pytest.raises(ValueError, match="Document not found"):
        await service.change_document_name(
            conversation_id,
            uuid4(),
            "renamed.md",
            user_id=uuid4(),
        )

    assert fake_vector_store.updated_source_filenames == []
