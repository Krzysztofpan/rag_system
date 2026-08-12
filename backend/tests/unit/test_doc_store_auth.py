"""Unit tests for DocumentStore user-scoped document access."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.models.conversation import Conversation
from app.db.models.document import Document, DocumentStatus
from app.db.models.document_report import DocumentReport
from app.services.doc_store import DocumentStore


def _session_with_document(document: Document | None) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = document
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
    store = DocumentStore(session)

    document = await store.create_document(
        conversation_id=conversation_id,
        filename="note.md",
        content_type="text/markdown",
        file_size_bytes=12,
    )

    assert document.conversation_id == conversation_id
    session.add.assert_called_once_with(document)
    statement = _source_count_update_statement(session.execute)
    assert statement.table.name == Conversation.__tablename__
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(document)


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
    store = DocumentStore(session)

    deleted = await store.delete_document(
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
    store = DocumentStore(session)

    with pytest.raises(ValueError, match="Document not found in conversation"):
        await store.delete_document(uuid4(), uuid4(), user_id=uuid4())


async def test_change_document_name_requires_ownership():
    user_id = uuid4()
    conversation_id = uuid4()
    document = Document(
        conversation_id=conversation_id,
        filename="old.md",
        status=DocumentStatus.ready,
    )
    session = _session_with_document(document)
    store = DocumentStore(session)

    new_name = await store.change_document_name(
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
    store = DocumentStore(session)

    with pytest.raises(ValueError, match="You have to define new name"):
        await store.change_document_name(
            document.conversation_id,
            document.id,
            "",
            user_id=uuid4(),
        )


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
    store = DocumentStore(session)

    result = await store.get_report(
        conversation_id,
        document.id,
        user_id=user_id,
    )

    assert result is report


async def test_get_documents_reports_returns_matching_rows_in_requested_order():
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
    store = DocumentStore(session)

    reports = await store.get_documents_reports(
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


async def test_get_documents_reports_returns_empty_list_without_query():
    session = AsyncMock()
    store = DocumentStore(session)

    reports = await store.get_documents_reports(uuid4(), [], user_id=uuid4())

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
    store = DocumentStore(session)

    with pytest.raises(ValueError, match="Report not found"):
        await store.get_report(
            document.conversation_id,
            document.id,
            user_id=uuid4(),
        )
