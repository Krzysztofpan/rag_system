import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chunk import Chunk
from app.db.models.conversation import Conversation
from app.db.models.document import Document, DocumentStatus
from app.db.models.document_report import DocumentReport
from app.schemas.origin import FileOrigin, YoutubeOrigin, dump_origin
from app.services.chunker import ChunkResult
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        vector_store: VectorStore | None = None,
    ):
        self.session = session
        self.vector_store = vector_store

    async def create_document(
        self,
        *,
        conversation_id: UUID,
        filename: str,
        content_type: str | None = None,
        origin: FileOrigin | YoutubeOrigin | None = None,
    ) -> Document:
        document = Document(
            conversation_id=conversation_id,
            filename=filename,
            content_type=content_type,
            origin=dump_origin(origin) if origin is not None else None,
            status=DocumentStatus.pending,
        )
        self.session.add(document)
        await self._adjust_source_count(conversation_id, 1)
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def mark_processing(self, document_id: UUID) -> Document:
        document = await self._get_by_id(document_id)
        document.status = DocumentStatus.processing
        document.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def get_conversation_documents(
        self,
        conversation_id: UUID,
        *,
        user_id: UUID,
    ) -> list[Document]:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        docs_result = await self.session.execute(
            select(Document).where(Document.conversation_id == conversation_id)
        )
        return list(docs_result.scalars().all())

    async def get_conversation_document_summaries(
        self,
        conversation_id: UUID,
        *,
        user_id: UUID,
    ) -> list[tuple[str, str]]:
        await self.get_conversation_documents(
            conversation_id,
            user_id=user_id,
        )

        rows = await self.session.execute(
            select(Document.filename, DocumentReport.summary)
            .join(DocumentReport, DocumentReport.document_id == Document.id)
            .where(
                Document.conversation_id == conversation_id,
                DocumentReport.summary.is_not(None),
            )
            .order_by(Document.created_at.asc())
        )
        return [
            (filename, summary)
            for filename, summary in rows.all()
            if summary
        ]

    async def delete_document(
        self,
        conversation_id: UUID,
        document_id: UUID,
        *,
        user_id: UUID,
    ) -> Document:
        document = await self.get_document(
            conversation_id,
            document_id,
            user_id=user_id,
        )
        await self.session.delete(document)
        await self._adjust_source_count(conversation_id, -1)
        await self.session.commit()
        self._delete_document_vectors(conversation_id, document_id)
        return document

    async def change_document_name(
        self,
        conversation_id: UUID,
        document_id: UUID,
        name: str,
        *,
        user_id: UUID,
    ) -> str:
        document = await self.get_document(
            conversation_id,
            document_id,
            user_id=user_id,
        )

        if not name:
            raise ValueError("You have to define new name.")

        document.filename = name
        await self.session.commit()
        await self.session.refresh(document)
        self._update_document_source_filename(
            conversation_id,
            document_id,
            document.filename,
        )
        return document.filename

    async def save_chunks(
        self,
        document_id: UUID,
        chunks: list[ChunkResult],
    ) -> list[tuple[UUID, ChunkResult]]:
        document = await self._get_by_id(document_id)

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
        self._set_document_ready(document)

        await self.session.commit()
        return stored

    async def update_document_origin(
        self,
        document_id: UUID,
        origin: FileOrigin | YoutubeOrigin,
    ) -> None:
        document = await self._get_by_id(document_id)
        document.origin = dump_origin(origin)
        document.updated_at = datetime.now(UTC)
        await self.session.commit()

    async def mark_failed(self, document_id: UUID, message: str) -> None:
        await self.session.rollback()
        document = await self._get_by_id(document_id)
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
        *,
        user_id: UUID,
    ) -> DocumentReport:
        return await self._require_report(
            conversation_id,
            document_id,
            user_id=user_id,
        )

    async def add_summary_to_report(
        self,
        summary: str,
        conversation_id: UUID,
        document_id: UUID,
        *,
        user_id: UUID,
    ) -> DocumentReport:
        report = await self._require_report(
            conversation_id,
            document_id,
            user_id=user_id,
        )
        report.summary = summary
        report.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(report)
        return report

    async def get_document(
        self,
        conversation_id: UUID,
        document_id: UUID,
        *,
        user_id: UUID,
    ) -> Document:
        documents = await self.get_documents(
            conversation_id,
            [document_id],
            user_id=user_id,
        )
        return documents[0]

    async def get_documents(
        self,
        conversation_id: UUID,
        document_ids: list[UUID],
        *,
        user_id: UUID,
    ) -> list[Document]:
        if not document_ids:
            result = await self.session.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
            if result.scalar_one_or_none() is None:
                raise ValueError(f"Conversation {conversation_id} not found")
            return []

        unique_ids = list(dict.fromkeys(document_ids))
        result = await self.session.execute(
            select(Document)
            .join(Conversation, Conversation.id == Document.conversation_id)
            .where(
                Document.id.in_(unique_ids),
                Document.conversation_id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        by_id = {document.id: document for document in result.scalars().all()}
        if set(by_id) != set(unique_ids):
            raise ValueError("Document not found in conversation")
        return [by_id[document_id] for document_id in unique_ids]

    async def get_chunk(
        self,
        conversation_id: UUID,
        chunk_id: UUID,
        *,
        user_id: UUID,
    ) -> tuple[Chunk, Document]:
        result = await self.session.execute(
            select(Chunk, Document)
            .join(Document, Document.id == Chunk.document_id)
            .join(Conversation, Conversation.id == Document.conversation_id)
            .where(
                Chunk.id == chunk_id,
                Document.conversation_id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        row = result.one_or_none()
        if row is None:
            raise ValueError("Chunk not found")
        return row[0], row[1]

    async def get_document_reports(
        self,
        conversation_id: UUID,
        document_ids: list[UUID],
        *,
        user_id: UUID,
    ) -> list[DocumentReport]:
        if not document_ids:
            return []

        result = await self.session.execute(
            select(DocumentReport)
            .join(Document, Document.id == DocumentReport.document_id)
            .join(Conversation, Conversation.id == Document.conversation_id)
            .where(
                DocumentReport.document_id.in_(document_ids),
                Document.conversation_id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        by_id = {report.document_id: report for report in result.scalars().all()}
        return [
            by_id[document_id]
            for document_id in document_ids
            if document_id in by_id
        ]

    def _set_document_ready(self, document: Document) -> None:
        document.status = DocumentStatus.ready
        document.updated_at = datetime.now(UTC)

    async def _require_report(
        self,
        conversation_id: UUID,
        document_id: UUID,
        *,
        user_id: UUID,
    ) -> DocumentReport:
        await self.get_document(
            conversation_id,
            document_id,
            user_id=user_id,
        )
        report = await self.session.get(DocumentReport, document_id)
        if report is None:
            raise ValueError("Report not found")
        return report

    async def _get_by_id(self, document_id: UUID) -> Document:
        document = await self.session.get(Document, document_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found")
        return document

    async def _adjust_source_count(self, conversation_id: UUID, delta: int) -> None:
        """Keep denormalized conversations.source_count in sync with documents."""
        if delta == 0:
            return

        expression = Conversation.source_count + delta
        if delta < 0:
            expression = func.greatest(0, expression)

        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                source_count=expression,
                updated_at=datetime.now(UTC),
            )
        )

    def _delete_document_vectors(
        self,
        conversation_id: UUID,
        document_id: UUID,
    ) -> None:
        if self.vector_store is None:
            return
        try:
            self.vector_store.delete_document_vectors(conversation_id, document_id)
        except Exception:
            logger.exception(
                "Pinecone vectors leftover after document delete: %s",
                document_id,
            )

    def _update_document_source_filename(
        self,
        conversation_id: UUID,
        document_id: UUID,
        source_filename: str,
    ) -> None:
        if self.vector_store is None:
            return
        try:
            self.vector_store.update_document_source_filename(
                conversation_id,
                document_id,
                source_filename,
            )
        except Exception:
            logger.exception(
                "Pinecone source_filename leftover after document rename: %s",
                document_id,
            )
