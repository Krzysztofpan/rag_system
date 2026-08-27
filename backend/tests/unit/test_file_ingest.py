from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.document_indexing_service import IngestResult
from app.services.file_ingest import FileIngestService
from app.services.parser.base import ParseQualityError


def _session_factory():
    session = MagicMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=session_cm)


def _ingest_result(document_id):
    return IngestResult(
        document_id=document_id,
        parsed_content="# Hello",
        chunk_ids=[uuid4()],
        parse_report={"ok": True},
        chunk_quality={"ok": True},
    )


async def test_file_ingest_indexes_and_cleans_up_temp(tmp_path):
    path = tmp_path / "note.md"
    path.write_text("# Hello")
    document_id = uuid4()
    indexing = MagicMock()
    indexing.ingest = AsyncMock(return_value=_ingest_result(document_id))
    summarize = AsyncMock()

    with (
        patch(
            "app.services.file_ingest.get_session_factory",
            return_value=_session_factory(),
        ),
        patch(
            "app.services.file_ingest.create_indexing_service",
            return_value=indexing,
        ),
        patch(
            "app.services.file_ingest.apply_document_summary",
            new=summarize,
        ),
    ):
        await FileIngestService().ingest(
            conversation_id=uuid4(),
            document_id=document_id,
            user_id=uuid4(),
            path=str(path),
            filename="note.md",
            content_type="text/markdown",
        )

    indexing.ingest.assert_awaited_once()
    upload = indexing.ingest.await_args.args[0]
    assert upload.filename == "note.md"
    assert indexing.ingest.await_args.kwargs["document_id"] == document_id
    summarize.assert_awaited_once()
    assert not path.exists()


async def test_file_ingest_marks_failed_and_cleans_up_temp(tmp_path):
    path = tmp_path / "note.md"
    path.write_text("# Hello")
    document_id = uuid4()
    indexing = MagicMock()
    indexing.ingest = AsyncMock(side_effect=RuntimeError("parse exploded"))
    document_service = MagicMock()
    document_service.mark_failed = AsyncMock()
    summarize = AsyncMock()

    with (
        patch(
            "app.services.file_ingest.get_session_factory",
            return_value=_session_factory(),
        ),
        patch(
            "app.services.file_ingest.create_indexing_service",
            return_value=indexing,
        ),
        patch(
            "app.services.file_ingest.create_document_service",
            return_value=document_service,
        ),
        patch(
            "app.services.file_ingest.apply_document_summary",
            new=summarize,
        ),
        pytest.raises(RuntimeError, match="parse exploded"),
    ):
        await FileIngestService().ingest(
            conversation_id=uuid4(),
            document_id=document_id,
            user_id=uuid4(),
            path=str(path),
            filename="note.md",
            content_type="text/markdown",
        )

    document_service.mark_failed.assert_awaited_once_with(document_id, "parse exploded")
    summarize.assert_not_called()
    assert not path.exists()


async def test_file_ingest_swallows_parse_quality_error_and_cleans_up_temp(tmp_path):
    path = tmp_path / "note.md"
    path.write_text("# Hello")
    document_id = uuid4()
    indexing = MagicMock()
    indexing.ingest = AsyncMock(
        side_effect=ParseQualityError("rejected", report={}, document_id=document_id)
    )
    document_service = MagicMock()
    document_service.mark_failed = AsyncMock()
    summarize = AsyncMock()

    with (
        patch(
            "app.services.file_ingest.get_session_factory",
            return_value=_session_factory(),
        ),
        patch(
            "app.services.file_ingest.create_indexing_service",
            return_value=indexing,
        ),
        patch(
            "app.services.file_ingest.create_document_service",
            return_value=document_service,
        ),
        patch(
            "app.services.file_ingest.apply_document_summary",
            new=summarize,
        ),
    ):
        await FileIngestService().ingest(
            conversation_id=uuid4(),
            document_id=document_id,
            user_id=uuid4(),
            path=str(path),
            filename="note.md",
            content_type="text/markdown",
        )

    document_service.mark_failed.assert_not_called()
    summarize.assert_not_called()
    assert not path.exists()
