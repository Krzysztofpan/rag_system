from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chunk import Chunk
from app.db.models.document import Document, DocumentStatus
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

    async def _get_document(self, document_id: UUID) -> Document:
        document = await self.session.get(Document, document_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found")
        return document
