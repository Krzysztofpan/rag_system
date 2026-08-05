from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chunk import Chunk
from app.db.models.document import Document, DocumentStatus
from app.db.models.document_report import DocumentReport
from app.services.chunker import ChunkResult


class DocumentStore:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_document(
        self,
        *,
        conversation_id: UUID,
        filename: str,
        content_type: str | None = None,
        file_size_bytes: int | None = None,
    ) -> Document:
        document = Document(
            conversation_id=conversation_id,
            filename=filename,
            content_type=content_type,
            file_size_bytes=file_size_bytes,
            status=DocumentStatus.pending,
        )
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def mark_processing(self, document_id: UUID) -> None:
        document = await self._get_document(document_id)
        document.status = DocumentStatus.processing
        document.updated_at = datetime.now(UTC)
        await self.session.commit()

    async def delete_document(
        self,
        conversation_id: UUID,
        document_id: UUID,
    ) -> Document:
        document = await self._require_document_in_conversation(
            conversation_id,
            document_id,
        )
        await self.session.delete(document)
        await self.session.commit()
        return document

    async def change_document_name(
        self,
        conversation_id: UUID,
        document_id: UUID,
        name: str
    ) -> str:
        document = await self._require_document_in_conversation(conversation_id, document_id)

        if(not name):
            raise ValueError("You have to define new name.")

        document.filename = name
        await self.session.commit()
        await self.session.refresh(document)
        return document.filename

    async def save_chunks(
        self,
        document_id: UUID,
        chunks: list[ChunkResult],
    ) -> list[tuple[UUID, ChunkResult]]:
        document = await self._get_document(document_id)

        stored: list[tuple[UUID, ChunkResult]] = []
        db_chunks: list[Chunk] = []
        for index, chunk in enumerate(chunks):
            db_chunk = Chunk(
                document_id=document_id,
                chunk_index=index,
                content=chunk.content,
                context=chunk.context,
                pages=chunk.pages,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                token_count=chunk.token_count,
            )
            db_chunks.append(db_chunk)
            stored.append((db_chunk.id, chunk))

        self.session.add_all(db_chunks)
        self._set_document_ready(document, chunks)

        await self.session.commit()
        return stored

    async def mark_failed(self, document_id: UUID, message: str) -> None:
        await self.session.rollback()
        document = await self._get_document(document_id)
        document.status = DocumentStatus.failed
        document.error_message = message
        document.updated_at = datetime.now(UTC)
        await self.session.commit()

    async def upsert_report(
        self,
        document_id: UUID,
        *,
        parsed_content: str | None,
        quality: dict[str, Any] | None,
    ) -> DocumentReport:
        report = await self.session.get(DocumentReport, document_id)
        if report is None:
            report = DocumentReport(document_id=document_id)
            self.session.add(report)

        report.parsed_content = parsed_content
        report.quality = quality
        report.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(report)
        return report

    async def get_report(
        self,
        conversation_id: UUID,
        document_id: UUID,
    ) -> DocumentReport:
        await self._require_document_in_conversation(conversation_id, document_id)
        report = await self.session.get(DocumentReport, document_id)
        if report is None:
            raise ValueError("Report not found")
        return report

    async def get_document(
        self,
        conversation_id: UUID,
        document_id: UUID,
    ) -> Document:
        return await self._require_document_in_conversation(
            conversation_id,
            document_id,
        )

    def _set_document_ready(
        self,
        document: Document,
        chunks: list[ChunkResult],
    ) -> None:
        token_counts = [c.token_count for c in chunks if c.token_count is not None]
        document.status = DocumentStatus.ready
        document.chunk_count = len(chunks)
        document.token_count = sum(token_counts) if token_counts else None
        document.updated_at = datetime.now(UTC)

    async def _require_document_in_conversation(
        self,
        conversation_id: UUID,
        document_id: UUID,
    ) -> Document:
        document = await self._get_document(document_id)
        if document.conversation_id != conversation_id:
            raise ValueError("Document not found in conversation")
        return document

    async def _get_document(self, document_id: UUID) -> Document:
        document = await self.session.get(Document, document_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found")
        return document
