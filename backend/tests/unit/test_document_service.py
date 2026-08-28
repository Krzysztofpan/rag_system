"""Unit tests for DocumentService user-scoped document access."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.models.conversation import Conversation
from app.db.models.document import Document, DocumentStatus
from app.db.models.document_report import DocumentReport
from app.schemas.origin import FileOrigin, YoutubeOrigin
from app.services.document_service import DocumentService
from tests.helpers import FakeVectorStore


def _session_with_document(document: Document | None) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = document
    result.scalars.return_value.all.return_value = [] if document is None else [document]
    session.execute = AsyncMock(return_value=result)
    return session


def _session_with_documents(documents: list[Document]) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = documents
    session.execute = AsyncMock(return_value=result)
    return session


def _source_count_update_statement(execute_mock: AsyncMock, *, index: int = -1):
    statement = execute_mock.await_args_list[index].args[0]
    assert statement.is_update
    return statement


async def test_create_document_increments_source_count():
    conversation_id = uuid4()
    session = AsyncMock()
    session.add = MagicMock()
    service = DocumentService(session)

    document = await service.create_document(
        conversation_id=conversation_id,
        filename="note.md",
        content_type="text/markdown",
        origin=FileOrigin(file_size_bytes=12),
    )

    assert document.conversation_id == conversation_id
    assert document.origin == {"kind": "file", "file_size_bytes": 12}
    session.add.assert_called_once_with(document)
    statement = _source_count_update_statement(session.execute)
    assert statement.table.name == Conversation.__tablename__
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(document)


async def test_update_document_origin_replaces_json():
    document_id = uuid4()
    document = Document(
        id=document_id,
        conversation_id=uuid4(),
        filename="youtube:dQw4w9wgXcQ",
        content_type="video/youtube",
        origin={"kind": "youtube", "video_id": "dQw4w9wgXcQ", "url": "https://youtu.be/dQw4w9wgXcQ"},
        status=DocumentStatus.processing,
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=document)
    service = DocumentService(session)

    await service.update_document_origin(
        document_id,
        YoutubeOrigin(
            video_id="dQw4w9wgXcQ",
            url="https://www.youtube.com/watch?v=dQw4w9wgXcQ",
            duration_sec=4.0,
            language="en",
            transcript_source="captions",
        ),
    )

    assert document.origin == {
        "kind": "youtube",
        "video_id": "dQw4w9wgXcQ",
        "url": "https://www.youtube.com/watch?v=dQw4w9wgXcQ",
        "duration_sec": 4.0,
        "language": "en",
        "transcript_source": "captions",
    }
    session.commit.assert_awaited_once()


async def test_delete_document_requires_ownership():
    user_id = uuid4()
    conversation_id = uuid4()
    document_id = uuid4()
    document = Document(
        id=document_id,
        conversation_id=conversation_id,
        filename="note.md",
        status=DocumentStatus.ready,
    )
    session = _session_with_document(document)
    service = DocumentService(session)

    deleted = await service.delete_document(
        conversation_id,
        document_id,
        user_id=user_id,
    )

    assert deleted is document
    session.delete.assert_called_once_with(document)
    assert session.execute.await_count == 2
    statement = _source_count_update_statement(session.execute)
    assert statement.table.name == Conversation.__tablename__
    session.commit.assert_awaited_once()


async def test_delete_document_raises_when_not_owned():
    session = _session_with_document(None)
    service = DocumentService(session)

    with pytest.raises(ValueError, match="Document not found in conversation"):
        await service.delete_document(uuid4(), uuid4(), user_id=uuid4())


async def test_delete_document_removes_sql_then_vectors():
    conversation_id = uuid4()
    document_id = uuid4()
    document = Document(
        id=document_id,
        conversation_id=conversation_id,
        filename="note.md",
        status=DocumentStatus.ready,
    )
    session = _session_with_document(document)
    vector_store = FakeVectorStore()
    service = DocumentService(session, vector_store)

    deleted = await service.delete_document(
        conversation_id,
        document_id,
        user_id=uuid4(),
    )

    assert deleted is document
    session.delete.assert_called_once_with(document)
    assert vector_store.deleted_documents == [(conversation_id, document_id)]
    assert vector_store.deleted_namespaces == []


async def test_delete_document_succeeds_when_pinecone_fails():
    conversation_id = uuid4()
    document = Document(
        conversation_id=conversation_id,
        filename="note.md",
        status=DocumentStatus.ready,
    )
    session = _session_with_document(document)
    vector_store = FakeVectorStore()
    vector_store.delete_document_vectors = MagicMock(
        side_effect=RuntimeError("pinecone down")
    )
    service = DocumentService(session, vector_store)

    deleted = await service.delete_document(
        conversation_id,
        document.id,
        user_id=uuid4(),
    )

    assert deleted is document
    session.commit.assert_awaited_once()


async def test_delete_document_skips_pinecone_when_sql_fails():
    vector_store = FakeVectorStore()
    service = DocumentService(_session_with_document(None), vector_store)

    with pytest.raises(ValueError, match="Document not found"):
        await service.delete_document(uuid4(), uuid4(), user_id=uuid4())

    assert vector_store.deleted_documents == []


async def test_change_document_name_requires_ownership():
    user_id = uuid4()
    conversation_id = uuid4()
    document = Document(
        conversation_id=conversation_id,
        filename="old.md",
        status=DocumentStatus.ready,
    )
    session = _session_with_document(document)
    service = DocumentService(session)

    new_name = await service.change_document_name(
        conversation_id,
        document.id,
        "new.md",
        user_id=user_id,
    )

    assert new_name == "new.md"
    assert document.filename == "new.md"
    session.commit.assert_awaited_once()


async def test_change_document_name_rejects_empty_name():
    document = Document(
        conversation_id=uuid4(),
        filename="old.md",
        status=DocumentStatus.ready,
    )
    session = _session_with_document(document)
    service = DocumentService(session)

    with pytest.raises(ValueError, match="You have to define new name"):
        await service.change_document_name(
            document.conversation_id,
            document.id,
            "",
            user_id=uuid4(),
        )


async def test_change_document_name_updates_sql_then_vector_metadata():
    conversation_id = uuid4()
    document = Document(
        conversation_id=conversation_id,
        filename="note.md",
        status=DocumentStatus.ready,
    )
    session = _session_with_document(document)
    vector_store = FakeVectorStore()
    service = DocumentService(session, vector_store)

    updated = await service.change_document_name(
        conversation_id,
        document.id,
        "renamed.md",
        user_id=uuid4(),
    )

    assert updated == "renamed.md"
    assert document.filename == "renamed.md"
    assert vector_store.updated_source_filenames == [
        (conversation_id, document.id, "renamed.md")
    ]


async def test_change_document_name_succeeds_when_pinecone_fails():
    conversation_id = uuid4()
    document = Document(
        conversation_id=conversation_id,
        filename="note.md",
        status=DocumentStatus.ready,
    )
    session = _session_with_document(document)
    vector_store = FakeVectorStore()
    vector_store.update_document_source_filename = MagicMock(
        side_effect=RuntimeError("pinecone down")
    )
    service = DocumentService(session, vector_store)

    updated = await service.change_document_name(
        conversation_id,
        document.id,
        "renamed.md",
        user_id=uuid4(),
    )

    assert updated == "renamed.md"
    assert document.filename == "renamed.md"


async def test_change_document_name_skips_pinecone_when_sql_fails():
    vector_store = FakeVectorStore()
    service = DocumentService(_session_with_document(None), vector_store)

    with pytest.raises(ValueError, match="Document not found"):
        await service.change_document_name(
            uuid4(),
            uuid4(),
            "renamed.md",
            user_id=uuid4(),
        )

    assert vector_store.updated_source_filenames == []


async def test_get_document_requires_ownership():
    user_id = uuid4()
    conversation_id = uuid4()
    document = Document(
        conversation_id=conversation_id,
        filename="note.md",
        status=DocumentStatus.ready,
    )
    session = _session_with_document(document)
    service = DocumentService(session)

    result = await service.get_document(
        conversation_id,
        document.id,
        user_id=user_id,
    )

    assert result is document


async def test_get_document_raises_when_not_owned():
    session = _session_with_document(None)
    service = DocumentService(session)

    with pytest.raises(ValueError, match="Document not found in conversation"):
        await service.get_document(uuid4(), uuid4(), user_id=uuid4())


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
    service = DocumentService(session)

    result = await service.get_conversation_documents(
        conversation.id,
        user_id=user_id,
    )

    assert result == documents
    assert session.execute.await_count == 2


async def test_get_conversation_document_summaries_skips_empty_and_orders():
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
    rows_result = MagicMock()
    rows_result.all.return_value = [
        ("go.md", "Go 1.27 notes"),
        ("empty.md", None),
        ("history.pdf", "Uprising sources"),
    ]
    session.execute = AsyncMock(
        side_effect=[ownership_result, documents_result, rows_result]
    )
    service = DocumentService(session)

    result = await service.get_conversation_document_summaries(
        conversation.id,
        user_id=user_id,
    )

    assert result == [
        ("go.md", "Go 1.27 notes"),
        ("history.pdf", "Uprising sources"),
    ]


async def test_get_ready_document_catalog_entries_includes_ready_without_summary():
    user_id = uuid4()
    conversation = Conversation(user_id=user_id)
    go_id = uuid4()
    history_id = uuid4()
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
    rows_result = MagicMock()
    rows_result.all.return_value = [
        (go_id, "go.md", "Go 1.27 notes"),
        (history_id, "history.pdf", None),
    ]
    session.execute = AsyncMock(
        side_effect=[ownership_result, documents_result, rows_result]
    )
    service = DocumentService(session)

    result = await service.get_ready_document_catalog_entries(
        conversation.id,
        user_id=user_id,
    )

    assert result == [
        (go_id, "go.md", "Go 1.27 notes"),
        (history_id, "history.pdf", None),
    ]


async def test_get_report_requires_document_in_conversation():
    user_id = uuid4()
    conversation_id = uuid4()
    document = Document(
        conversation_id=conversation_id,
        filename="note.md",
        status=DocumentStatus.ready,
    )
    report = DocumentReport(
        document_id=document.id,
        parsed_content="# Title",
        quality={"ok": True},
    )
    session = _session_with_document(document)
    session.get = AsyncMock(return_value=report)
    service = DocumentService(session)

    result = await service.get_report(
        conversation_id,
        document.id,
        user_id=user_id,
    )

    assert result is report


async def test_get_documents_checks_owner_and_membership():
    user_id = uuid4()
    conversation_id = uuid4()
    first = Document(
        conversation_id=conversation_id,
        filename="a.md",
        status=DocumentStatus.ready,
    )
    second = Document(
        conversation_id=conversation_id,
        filename="b.md",
        status=DocumentStatus.ready,
    )
    session = _session_with_documents([second, first])
    service = DocumentService(session)

    documents = await service.get_documents(
        conversation_id,
        [first.id, second.id],
        user_id=user_id,
    )

    assert documents == [first, second]
    session.execute.assert_awaited_once()
    compiled = str(session.execute.await_args.args[0].compile()).lower()
    assert "documents" in compiled
    assert "conversations" in compiled
    assert "user_id" in compiled


async def test_get_documents_raises_when_conversation_not_owned():
    session = _session_with_documents([])
    service = DocumentService(session)

    with pytest.raises(ValueError, match="Document not found in conversation"):
        await service.get_documents(uuid4(), [uuid4()], user_id=uuid4())


async def test_get_documents_raises_when_document_is_foreign():
    owned = Document(
        conversation_id=uuid4(),
        filename="owned.md",
        status=DocumentStatus.ready,
    )
    session = _session_with_documents([owned])
    service = DocumentService(session)

    with pytest.raises(ValueError, match="Document not found in conversation"):
        await service.get_documents(
            owned.conversation_id,
            [owned.id, uuid4()],
            user_id=uuid4(),
        )


async def test_get_documents_allows_empty_document_ids():
    user_id = uuid4()
    conversation = Conversation(user_id=user_id)
    session = _session_with_document(conversation)
    service = DocumentService(session)

    documents = await service.get_documents(
        conversation.id,
        [],
        user_id=user_id,
    )

    assert documents == []
    session.execute.assert_awaited_once()


async def test_get_documents_raises_when_empty_ids_and_conversation_missing():
    conversation_id = uuid4()
    session = _session_with_document(None)
    service = DocumentService(session)

    with pytest.raises(ValueError, match=f"Conversation {conversation_id} not found"):
        await service.get_documents(conversation_id, [], user_id=uuid4())


async def test_get_document_reports_returns_matching_rows_in_requested_order():
    user_id = uuid4()
    conversation_id = uuid4()
    first = DocumentReport(
        document_id=uuid4(),
        parsed_content="first content",
    )
    second = DocumentReport(
        document_id=uuid4(),
        parsed_content="second content",
    )
    missing_id = uuid4()
    session = _session_with_documents([second, first])
    service = DocumentService(session)

    reports = await service.get_document_reports(
        conversation_id,
        [first.document_id, missing_id, second.document_id],
        user_id=user_id,
    )

    assert reports == [first, second]
    statement = session.execute.await_args.args[0]
    compiled = str(statement.compile()).lower()
    assert "document_reports" in compiled
    assert "conversations" in compiled
    assert "user_id" in compiled


async def test_get_document_reports_returns_empty_list_without_query():
    session = AsyncMock()
    service = DocumentService(session)

    reports = await service.get_document_reports(uuid4(), [], user_id=uuid4())

    assert reports == []
    session.execute.assert_not_awaited()


async def test_get_report_raises_when_report_missing():
    document = Document(
        conversation_id=uuid4(),
        filename="note.md",
        status=DocumentStatus.ready,
    )
    session = _session_with_document(document)
    session.get = AsyncMock(return_value=None)
    service = DocumentService(session)

    with pytest.raises(ValueError, match="Report not found"):
        await service.get_report(
            document.conversation_id,
            document.id,
            user_id=uuid4(),
        )


def _session_with_row(row):
    session = AsyncMock()
    result = MagicMock()
    result.one_or_none.return_value = row
    session.execute = AsyncMock(return_value=result)
    return session


async def test_get_chunk_returns_owned_chunk():
    conversation_id = uuid4()
    chunk_id = uuid4()
    chunk = SimpleNamespace(id=chunk_id, content="body")
    document = Document(
        conversation_id=conversation_id,
        filename="regulamin.pdf",
        status=DocumentStatus.ready,
    )
    session = _session_with_row((chunk, document))
    service = DocumentService(session)

    got_chunk, got_document = await service.get_chunk(
        conversation_id,
        chunk_id,
        user_id=uuid4(),
    )

    assert got_chunk is chunk
    assert got_document is document
    session.execute.assert_awaited_once()


async def test_get_chunk_raises_when_missing():
    session = _session_with_row(None)
    service = DocumentService(session)

    with pytest.raises(ValueError, match="Chunk not found"):
        await service.get_chunk(uuid4(), uuid4(), user_id=uuid4())
