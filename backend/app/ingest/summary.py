from uuid import UUID

from app.container import get_conversation_event_broker
from app.lib.tracing import conversation_tracing
from app.services.chunker.factory import ChunkerFactory
from app.services.conversation_events import conversation_updated_event
from app.services.document_indexing_service import DocumentIndexingService
from app.services.documents_catalog import store_documents_catalog
from app.services.parser.factory import ParserFactory


async def apply_document_summary(
    parsed_content: str,
    conversation_id: UUID,
    document_id: UUID,
    user_id: UUID,
) -> None:
    with conversation_tracing(
        conversation_id,
        user_id=user_id,
        tags=["ingest"],
        extra_metadata={"document_id": document_id},
    ):
        indexing_service = DocumentIndexingService(
            parser_factory=ParserFactory(),
            chunker_factory=ChunkerFactory(),
        )
        per_doc_summary = await indexing_service.summarize_document(
            parsed_content,
            conversation_id,
            document_id,
            user_id,
        )

        title, topic, documents_summary = await store_documents_catalog(
            conversation_id,
            user_id,
            fallback_summary=per_doc_summary,
            update_metadata=True,
        )

        await get_conversation_event_broker().publish(
            conversation_id,
            conversation_updated_event(
                conversation_id,
                title,
                topic,
                documents_summary,
            ),
        )
