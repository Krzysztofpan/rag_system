from dataclasses import dataclass
from uuid import UUID

from fastapi import UploadFile

from app.db.session import get_session_factory
from app.lib.file_types import FileTypes
from app.lib.tracing import conversation_tracing
from app.prompts import DOCUMENT_SUMMARY_TEMPLATE
from app.schemas.origin import FileOrigin
from app.schemas.upload import build_upload_quality, quality_from_rejected_report
from app.services.chunker import ChunkerFactory, Chunker
from app.services.document_service import DocumentService
from app.services.parser import ParseQualityError, ParseResult, ParserFactory, Parser
from app.services.parser.complex.quality_audit import ensure_chunk_quality
from app.services.vector_store import VectorStore
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


@dataclass(frozen=True)
class IngestResult:
    document_id: UUID
    parsed_content: str
    chunk_ids: list[UUID]
    parse_report: dict
    chunk_quality: dict


class DocumentIndexingService:
    def __init__(
        self,
        parser_factory: ParserFactory,
        chunker_factory: ChunkerFactory,
        document_service: DocumentService | None = None,
        vector_store: VectorStore | None = None,
    ):
        self.document_service = document_service
        self.vector_store = vector_store
        self.parser_factory = parser_factory
        self.chunker_factory = chunker_factory

    async def summarize_document(
            self, 
            document_parsed_content: str,
            conversation_id: UUID, 
            document_id: UUID, 
            user_id: UUID
    ) -> str:
        prompt = ChatPromptTemplate.from_template(DOCUMENT_SUMMARY_TEMPLATE)
        
        summarization_llm = ChatOpenAI(model="gpt-4o-mini")
  
        summary_chain = prompt | summarization_llm | StrOutputParser()

        summary = await summary_chain.ainvoke(
            {"document_content": document_parsed_content},
            config={"run_name": "summarize_document"},
        )

        session_factory = get_session_factory()
        async with session_factory() as session:
            store = DocumentService(session)
            await store.add_summary_to_report(
                summary,
                conversation_id,
                document_id,
                user_id=user_id,
            )
        
        return summary

    def create_parser(self, file: UploadFile) -> Parser:
        return self.parser_factory.create_parser(file)

    def create_chunker(
        self,
        content_type: str | FileTypes | None,
        filename: str | None = None,
    ) -> Chunker:
        return self.chunker_factory.create_chunker(
            content_type,
            filename=filename,
        )

    def _require_services(self) -> tuple[DocumentService, VectorStore]:
        if self.document_service is None:
            raise RuntimeError("DocumentService is required")
        if self.vector_store is None:
            raise RuntimeError("VectorStore is required")
        return self.document_service, self.vector_store

    async def ingest(self, file: UploadFile, *, conversation_id: UUID) -> IngestResult:
        with conversation_tracing(conversation_id, tags=["ingest"]):
            parser = self.create_parser(file)
            document_service, _ = self._require_services()

            document = await document_service.create_document(
                conversation_id=conversation_id,
                filename=file.filename or "unknown",
                content_type=file.content_type,
                origin=FileOrigin(file_size_bytes=file.size),
            )

            document_id = document.id
            await document_service.mark_processing(document_id)

            try:
                parsed = await parser._parse()
            except Exception as exc:
                await document_service.mark_failed(document_id, str(exc))
                raise

            return await self.index_parsed(
                document_id=document_id,
                conversation_id=conversation_id,
                parsed=parsed,
                source_filename=file.filename or "unknown",
                content_type=file.content_type,
            )

    async def index_parsed(
        self,
        *,
        document_id: UUID,
        conversation_id: UUID,
        parsed: ParseResult,
        source_filename: str,
        content_type: str | FileTypes | None,
    ) -> IngestResult:
        """Chunk, store, and embed an already-created document from a ParseResult."""
        document_service, vector_store = self._require_services()
        chunker = self.create_chunker(
            content_type,
            filename=source_filename,
        )
        parsed_markdown: str = parsed.markdown

        try:
            doc = parsed.document if parsed.document is not None else parsed.markdown
            chunks = chunker._chunk(doc=doc, source_text=parsed.markdown)

            kept, chunk_quality = ensure_chunk_quality(
                chunks,
                parse_report=parsed.report,
            )

            stored = await document_service.save_chunks(document_id, kept)

            vectors = vector_store.construct_vectors(
                stored,
                document_id=document_id,
                source_filename=source_filename,
            )

            vector_store.add_vectors(
                vectors,
                conversation_id=conversation_id,
            )

            quality = build_upload_quality(
                parse_report=parsed.report,
                chunk_quality=chunk_quality,
            )
            await document_service.upsert_report(
                document_id,
                parsed_content=parsed.markdown,
                quality=quality.model_dump(mode="json"),
            )

            return IngestResult(
                document_id=document_id,
                parsed_content=parsed.markdown,
                chunk_ids=[chunk_id for chunk_id, _ in stored],
                parse_report=parsed.report,
                chunk_quality=chunk_quality,
            )
        except ParseQualityError as exc:
            await document_service.mark_failed(document_id, str(exc))
            quality = quality_from_rejected_report(exc.report)
            await document_service.upsert_report(
                document_id,
                parsed_content=parsed_markdown,
                quality=quality.model_dump(mode="json") if quality is not None else None,
            )
            raise ParseQualityError(
                str(exc),
                report=exc.report,
                document_id=document_id,
                parsed_content=parsed_markdown,
            ) from exc
        except Exception as exc:
            await document_service.mark_failed(document_id, str(exc))
            raise
