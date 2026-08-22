"""End-to-end orchestration tests for DocumentIndexingService.ingest."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.db.models.document import DocumentStatus
from app.services.chunker.factory import ChunkerFactory
from app.services.chunker.simple import SimpleChunker
from app.services.document_indexing_service import DocumentIndexingService
from app.services.parser.base import ParseQualityError, ParseResult
from app.services.parser.complex.ocr_repair import REPLACEMENT_CHAR
from app.services.parser.factory import ParserFactory
from app.services.parser.simple import SimpleParser
from app.lib.file_types import FileTypes
from tests.helpers import (
    FakeChunker,
    FakeChunkerFactory,
    FakeParser,
    FakeParserFactory,
    FakeVectorStore,
    make_chunk,
    make_fake_docling_document,
    make_upload_file,
)


def _service(
    *,
    parser_factory=None,
    chunker_factory=None,
    document_service=None,
    vector_store=None,
) -> DocumentIndexingService:
    return DocumentIndexingService(
        parser_factory=parser_factory or ParserFactory(),
        chunker_factory=chunker_factory or ChunkerFactory(),
        document_service=document_service,
        vector_store=vector_store,
    )


async def test_ingest_requires_document_service(markdown_upload, conversation_id):
    service = _service(vector_store=FakeVectorStore())
    with pytest.raises(RuntimeError, match="DocumentService is required"):
        await service.ingest(markdown_upload, conversation_id=conversation_id)


async def test_ingest_requires_vector_store(markdown_upload, conversation_id, fake_document_service):
    service = _service(document_service=fake_document_service)
    with pytest.raises(RuntimeError, match="VectorStore is required"):
        await service.ingest(markdown_upload, conversation_id=conversation_id)


async def test_ingest_simple_path_happy(
    markdown_upload,
    conversation_id,
    fake_document_service,
    fake_vector_store,
):
    """MD/TXT: real SimpleParser + SimpleChunker through the full ingest pipeline."""
    service = _service(document_service=fake_document_service, vector_store=fake_vector_store)

    result = await service.ingest(markdown_upload, conversation_id=conversation_id)

    document = fake_document_service.documents[result.document_id]
    assert document.status == DocumentStatus.ready
    assert document.filename == "note.md"
    assert result.parsed_content.startswith("# Title")
    assert result.chunk_ids
    assert result.parse_report["ok"] is True
    assert result.chunk_quality["ok"] is True
    assert result.chunk_quality["kept_chunks"] == len(result.chunk_ids)
    assert len(fake_vector_store.added) == 1
    vectors, ns = fake_vector_store.added[0]
    assert ns == conversation_id
    assert len(vectors) == len(result.chunk_ids)
    assert [e[0] for e in fake_document_service.events[:2]] == ["create", "processing"]


async def test_ingest_text_path_uses_simple_parser_and_chunker(
    text_upload,
    conversation_id,
    fake_document_service,
    fake_vector_store,
):
    service = _service(document_service=fake_document_service, vector_store=fake_vector_store)
    result = await service.ingest(text_upload, conversation_id=conversation_id)

    assert "Plain text" in result.parsed_content
    assert fake_document_service.documents[result.document_id].status == DocumentStatus.ready
    assert fake_vector_store.added


async def test_ingest_complex_path_passes_docling_document_to_chunker(
    pdf_upload,
    conversation_id,
    fake_document_service,
    fake_vector_store,
):
    """PDF/DOCX: ComplexParser (mocked convert) + chunker receives DoclingDocument."""
    fake_doc = make_fake_docling_document("# PDF Title\n\nParsed PDF body for chunking.")
    captured: dict = {}

    class CapturingChunkerFactory:
        def create_chunker(self, content_type, filename=None):
            assert content_type == FileTypes.PDF

            class Wrapper:
                def _chunk(self, *, doc, source_text: str):
                    captured["doc"] = doc
                    captured["source_text"] = source_text
                    return [
                        make_chunk(
                            "Parsed PDF body for chunking.",
                            context="PDF Title",
                            pages=[1],
                            char_start=0,
                            char_end=10,
                            token_count=5,
                        )
                    ]

            return Wrapper()

    with patch(
        "app.services.parser.complex.parser.convert_document",
        return_value=fake_doc,
    ):
        service = _service(
            parser_factory=ParserFactory(),
            chunker_factory=CapturingChunkerFactory(),
            document_service=fake_document_service,
            vector_store=fake_vector_store,
        )
        result = await service.ingest(pdf_upload, conversation_id=conversation_id)

    assert captured["doc"] is fake_doc
    assert captured["source_text"] == "# PDF Title\n\nParsed PDF body for chunking."
    assert result.parsed_content.startswith("# PDF Title")
    assert result.chunk_ids
    assert fake_vector_store.added[0][1] == conversation_id


async def test_ingest_docx_complex_path(
    docx_upload,
    conversation_id,
    fake_document_service,
    fake_vector_store,
):
    fake_doc = make_fake_docling_document("DOCX content")

    class StubChunkerFactory:
        def create_chunker(self, content_type, filename=None):
            assert content_type == FileTypes.DOCX
            return FakeChunker([make_chunk("DOCX content", token_count=2)])

    with patch(
        "app.services.parser.complex.parser.convert_document",
        return_value=fake_doc,
    ):
        service = _service(
            chunker_factory=StubChunkerFactory(),
            document_service=fake_document_service,
            vector_store=fake_vector_store,
        )
        result = await service.ingest(docx_upload, conversation_id=conversation_id)

    assert result.parsed_content == "DOCX content"
    assert fake_document_service.documents[result.document_id].status == DocumentStatus.ready


async def test_ingest_marks_failed_on_parse_quality_error(
    conversation_id,
    fake_document_service,
    fake_vector_store,
):
    upload = make_upload_file("x", content_type=FileTypes.MD, filename="bad.md")
    bad_chunks = [
        make_chunk(f"bad {REPLACEMENT_CHAR}"),
        make_chunk(f"also bad {REPLACEMENT_CHAR}"),
        make_chunk("good"),
        make_chunk(f"still bad {REPLACEMENT_CHAR}"),
    ]
    parser = FakeParser(
        upload,
        ParseResult(markdown="x", report={"ok": True}),
    )
    service = _service(
        parser_factory=FakeParserFactory(parser),
        chunker_factory=FakeChunkerFactory(FakeChunker(bad_chunks)),
        document_service=fake_document_service,
        vector_store=fake_vector_store,
    )

    with pytest.raises(ParseQualityError) as exc_info:
        await service.ingest(upload, conversation_id=conversation_id)

    document_id = exc_info.value.document_id
    assert document_id is not None
    assert fake_document_service.documents[document_id].status == DocumentStatus.failed
    assert "Document rejected" in (fake_document_service.documents[document_id].error_message or "")
    assert not fake_vector_store.added
    assert "failed" in {e[0] for e in fake_document_service.events}


async def test_ingest_marks_failed_on_generic_error(
    conversation_id,
    fake_document_service,
    fake_vector_store,
):
    upload = make_upload_file("x", content_type=FileTypes.MD, filename="boom.md")

    class BoomParser(FakeParser):
        async def _parse(self) -> ParseResult:
            raise RuntimeError("parse exploded")

    service = _service(
        parser_factory=FakeParserFactory(
            BoomParser(upload, ParseResult(markdown="", report={}))
        ),
        chunker_factory=FakeChunkerFactory(FakeChunker([])),
        document_service=fake_document_service,
        vector_store=fake_vector_store,
    )

    with pytest.raises(RuntimeError, match="parse exploded"):
        await service.ingest(upload, conversation_id=conversation_id)

    document = next(iter(fake_document_service.documents.values()))
    assert document.status == DocumentStatus.failed
    assert document.error_message == "parse exploded"
    assert not fake_vector_store.added


async def test_ingest_simple_path_passes_markdown_string_as_doc(
    conversation_id,
    fake_document_service,
    fake_vector_store,
):
    """When ParseResult.document is None, chunker receives markdown string."""
    upload = make_upload_file("hello chunk", content_type=FileTypes.TXT, filename="a.txt")
    parser = FakeParser(
        upload,
        ParseResult(markdown="hello chunk", report={"ok": True}, document=None),
    )
    chunker = FakeChunker([make_chunk("hello chunk", token_count=2)])
    service = _service(
        parser_factory=FakeParserFactory(parser),
        chunker_factory=FakeChunkerFactory(chunker),
        document_service=fake_document_service,
        vector_store=fake_vector_store,
    )

    await service.ingest(upload, conversation_id=conversation_id)

    assert chunker.calls[0]["doc"] == "hello chunk"
    assert chunker.calls[0]["source_text"] == "hello chunk"


async def test_create_parser_and_chunker_delegate_to_factories(markdown_upload):
    service = _service()
    assert isinstance(service.create_parser(markdown_upload), SimpleParser)
    assert isinstance(service.create_chunker(markdown_upload), SimpleChunker)


async def test_summarize_document_writes_with_a_fresh_session(fake_document_service):
    conversation_id = uuid4()
    document_id = uuid4()
    user_id = uuid4()

    chain = MagicMock()
    chain.__or__.return_value = chain
    chain.ainvoke = AsyncMock(return_value="A short summary")

    session = MagicMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    session_factory = MagicMock(return_value=session_cm)

    store = MagicMock()
    store.add_summary_to_report = AsyncMock()

    service = _service(document_service=fake_document_service)

    with (
        patch(
            "app.services.document_indexing_service.ChatPromptTemplate.from_template",
            return_value=chain,
        ),
        patch("app.services.document_indexing_service.ChatOpenAI"),
        patch(
            "app.services.document_indexing_service.get_session_factory",
            return_value=session_factory,
        ),
        patch(
            "app.services.document_indexing_service.DocumentService",
            return_value=store,
        ) as store_cls,
    ):
        await service.summarize_document(
            "# Doc",
            conversation_id,
            document_id,
            user_id,
        )

    chain.ainvoke.assert_awaited_once_with(
        {"document_content": "# Doc"},
        config={"run_name": "summarize_document"},
    )
    store_cls.assert_called_once_with(session)
    store.add_summary_to_report.assert_awaited_once_with(
        "A short summary",
        conversation_id,
        document_id,
        user_id=user_id,
    )
    assert not any(event[0] == "add_summary" for event in fake_document_service.events)
