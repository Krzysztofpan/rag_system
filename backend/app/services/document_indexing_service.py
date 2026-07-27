from dataclasses import dataclass
from uuid import UUID

from fastapi import UploadFile

from app.config import get_settings
from app.services.chunker import ChunkResult, Chunker
from app.services.doc_store import DocumentStore
from app.services.parser import ParseQualityError, Parser
from app.services.parser.complex.quality_audit import evaluate_chunk_quality


@dataclass(frozen=True)
class IngestResult:
    document_id: UUID
    chunks: list[ChunkResult]
    chunk_ids: list[UUID]
    parse_report: dict
    chunk_quality: dict


class DocumentIndexingService:
    def __init__(
        self,
        parser: Parser,
        chunker: Chunker,
        doc_store: DocumentStore | None = None,
        vector_store=None,
        embedder=None,
    ):
        self.doc_store = doc_store
        self.vector_store = vector_store
        self.embedder = embedder
        self.parser = parser
        self.chunker = chunker

    async def ingest(self, file: UploadFile) -> IngestResult:
        if self.doc_store is None:
            raise RuntimeError("DocumentStore is required for ingest")

        settings = get_settings()
        document = await self.doc_store.create_document(
            filename=file.filename or "unknown",
            content_type=file.content_type,
            file_size_bytes=file.size,
        )
        document_id = document.id
        await self.doc_store.mark_processing(document_id)

        try:
            parsed = await self.parser._parse()
            doc = parsed.document if parsed.document is not None else parsed.markdown
            chunks = self.chunker._chunk(doc=doc, source_text=parsed.markdown)

            chunk_quality = evaluate_chunk_quality(
                chunks,
                max_rejected_ratio=settings.parser_max_rejected_chunk_ratio,
            )
            report = {
                **parsed.report,
                "chunk_quality": chunk_quality,
            }

            if not chunk_quality["ok"]:
                rejected = chunk_quality["rejected_chunks"]
                total = chunk_quality["total_chunks"]
                ratio = chunk_quality["rejected_ratio"]
                threshold = chunk_quality["max_rejected_ratio"]
                raise ParseQualityError(
                    (
                        f"Document rejected: {rejected}/{total} chunks "
                        f"({ratio:.0%}) failed quality checks "
                        f"(threshold {threshold:.0%})"
                    ),
                    report=report,
                )

            kept_indexes = chunk_quality["kept_indexes"]
            kept = [chunks[i] for i in kept_indexes]
            stored = await self.doc_store.save_chunks(document_id, kept)
            return IngestResult(
                document_id=document_id,
                chunks=kept,
                chunk_ids=[chunk_id for chunk_id, _ in stored],
                parse_report=parsed.report,
                chunk_quality=chunk_quality,
            )
        except ParseQualityError as exc:
            await self.doc_store.mark_failed(document_id, str(exc))
            raise ParseQualityError(
                str(exc),
                report=exc.report,
                document_id=document_id,
            ) from exc
        except Exception as exc:
            await self.doc_store.mark_failed(document_id, str(exc))
            raise
