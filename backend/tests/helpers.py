"""Shared helpers and fakes for the document indexing pipeline tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import UploadFile
from starlette.datastructures import Headers

from app.db.models.document import Document, DocumentStatus
from app.schemas.origin import FileOrigin, YoutubeOrigin, dump_origin
from app.services.chunker.base import ChunkResult
from app.services.parser.base import ParseResult, Parser


def make_upload_file(
    content: bytes | str,
    *,
    content_type: str,
    filename: str = "sample.bin",
) -> UploadFile:
    payload = content.encode("utf-8") if isinstance(content, str) else content
    return UploadFile(
        file=BytesIO(payload),
        filename=filename,
        size=len(payload),
        headers=Headers({"content-type": content_type}),
    )


def make_chunk(
    content: str,
    *,
    context: str | None = None,
    pages: list[int] | None = None,
    char_start: int | None = None,
    char_end: int | None = None,
    token_count: int | None = None,
) -> ChunkResult:
    return ChunkResult(
        content=content,
        context=context,
        pages=pages,
        char_start=char_start,
        char_end=char_end,
        token_count=token_count if token_count is not None else max(1, len(content.split())),
    )


def make_fake_docling_document(markdown: str = "# Doc\n\nBody text.") -> SimpleNamespace:
    """Minimal stand-in for DoclingDocument used by the complex path."""
    return SimpleNamespace(
        export_to_markdown=lambda: markdown,
        _markdown=markdown,
    )


class FakeParser(Parser):
    def __init__(self, file: UploadFile, result: ParseResult):
        super().__init__(file)
        self._result = result

    async def _parse(self) -> ParseResult:
        return self._result


class FakeChunker:
    def __init__(self, chunks: list[ChunkResult]):
        self._chunks = chunks
        self.calls: list[dict] = []

    def _chunk(self, *, doc, source_text: str) -> list[ChunkResult]:
        self.calls.append({"doc": doc, "source_text": source_text})
        return list(self._chunks)


class FakeParserFactory:
    def __init__(self, parser: Parser):
        self.parser = parser
        self.calls: list[UploadFile] = []

    def create_parser(self, file: UploadFile) -> Parser:
        self.calls.append(file)
        return self.parser


class FakeChunkerFactory:
    def __init__(self, chunker: FakeChunker):
        self.chunker = chunker
        self.calls: list[str | None] = []

    def create_chunker(self, content_type, filename=None) -> FakeChunker:
        self.calls.append(content_type)
        return self.chunker


@dataclass
class FakeDocumentService:
    documents: dict[UUID, Document] = field(default_factory=dict)
    saved_chunks: dict[UUID, list[ChunkResult]] = field(default_factory=dict)
    reports: dict[UUID, dict] = field(default_factory=dict)
    events: list[tuple[str, UUID, object | None]] = field(default_factory=list)

    async def create_document(
        self,
        *,
        conversation_id: UUID,
        filename: str,
        content_type: str | None = None,
        origin: FileOrigin | YoutubeOrigin | None = None,
    ) -> Document:
        document = Document(
            id=uuid4(),
            conversation_id=conversation_id,
            filename=filename,
            content_type=content_type,
            origin=dump_origin(origin) if origin is not None else None,
            status=DocumentStatus.pending,
        )
        self.documents[document.id] = document
        self.events.append(("create", document.id, filename))
        return document

    async def mark_processing(self, document_id: UUID) -> None:
        self.documents[document_id].status = DocumentStatus.processing
        self.events.append(("processing", document_id, None))

    async def save_chunks(
        self,
        document_id: UUID,
        chunks: list[ChunkResult],
    ) -> list[tuple[UUID, ChunkResult]]:
        document = self.documents[document_id]
        document.status = DocumentStatus.ready
        document.chunk_count = len(chunks)
        document.token_count = sum(c.token_count or 0 for c in chunks) or None
        self.saved_chunks[document_id] = list(chunks)
        stored = [(uuid4(), chunk) for chunk in chunks]
        self.events.append(("save_chunks", document_id, len(chunks)))
        return stored

    async def update_document_origin(
        self,
        document_id: UUID,
        origin: FileOrigin | YoutubeOrigin,
    ) -> None:
        self.documents[document_id].origin = dump_origin(origin)
        self.events.append(("update_origin", document_id, origin))

    async def mark_failed(self, document_id: UUID, message: str) -> None:
        document = self.documents[document_id]
        document.status = DocumentStatus.failed
        document.error_message = message
        self.events.append(("failed", document_id, message))

    async def upsert_report(
        self,
        document_id: UUID,
        *,
        parsed_content: str | None,
        quality: dict | None,
    ) -> None:
        self.events.append(("upsert_report", document_id, parsed_content))
        self.reports[document_id] = {
            "parsed_content": parsed_content,
            "quality": quality,
        }

    async def add_summary_to_report(
        self,
        summary: str,
        conversation_id: UUID,
        document_id: UUID,
        *,
        user_id: UUID,
    ) -> None:
        self.events.append(("add_summary", document_id, summary))
        report = self.reports.setdefault(document_id, {})
        report["summary"] = summary

    async def delete_document(
        self,
        conversation_id: UUID,
        document_id: UUID,
        *,
        user_id: UUID,
    ) -> Document:
        document = self.documents.pop(document_id)
        self.events.append(("delete", document_id, conversation_id))
        return document

    async def change_document_name(
        self,
        conversation_id: UUID,
        document_id: UUID,
        name: str,
        *,
        user_id: UUID,
    ) -> str:
        if not name:
            raise ValueError("You have to define new name.")
        document = self.documents[document_id]
        document.filename = name
        self.events.append(("rename", document_id, name))
        return document.filename


@dataclass
class FakeVectorStore:
    vectors: list[dict] = field(default_factory=list)
    added: list[tuple[list[dict], UUID]] = field(default_factory=list)
    deleted_namespaces: list[UUID] = field(default_factory=list)
    deleted_documents: list[tuple[UUID, UUID]] = field(default_factory=list)
    updated_source_filenames: list[tuple[UUID, UUID, str]] = field(default_factory=list)

    def construct_vectors(
        self,
        stored_chunks: list[tuple[UUID, ChunkResult]],
        *,
        document_id: UUID,
        source_filename: str,
    ) -> list[dict]:
        built = [
            {
                "id": str(chunk_id),
                "values": [0.1, 0.2],
                "metadata": {
                    "document_id": str(document_id),
                    "chunk_index": index,
                    "source_filename": source_filename,
                },
            }
            for index, (chunk_id, _) in enumerate(stored_chunks)
        ]
        self.vectors = built
        return built

    def add_vectors(self, vectors, *, conversation_id: UUID) -> None:
        self.added.append((list(vectors), conversation_id))

    def delete_namespace(self, conversation_id: UUID) -> None:
        self.deleted_namespaces.append(conversation_id)

    def delete_document_vectors(
        self,
        conversation_id: UUID,
        document_id: UUID,
    ) -> None:
        self.deleted_documents.append((conversation_id, document_id))

    def update_document_source_filename(
        self,
        conversation_id: UUID,
        document_id: UUID,
        source_filename: str,
    ) -> None:
        self.updated_source_filenames.append(
            (conversation_id, document_id, source_filename)
        )
