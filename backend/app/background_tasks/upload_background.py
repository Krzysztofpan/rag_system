from uuid import UUID

from app.container import (
    create_conversation_memory_service,
    create_conversation_service,
    create_document_service,
    get_conversation_event_broker,
)
from app.db.session import get_session_factory
from app.lib.tracing import conversation_tracing
from app.services.chunker.factory import ChunkerFactory
from app.services.conversation_documents_summary import ConversationDocumentsSummarizer
from app.services.conversation_events import conversation_updated_event
from app.services.document_indexing_service import DocumentIndexingService
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

        title, topic, documents_summary = await _store_documents_catalog(
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


async def refresh_and_publish_documents_summary(
    conversation_id: UUID,
    user_id: UUID,
) -> None:
    title, topic, documents_summary = await _store_documents_catalog(
        conversation_id,
        user_id,
        fallback_summary=None,
        update_metadata=False,
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


async def _store_documents_catalog(
    conversation_id: UUID,
    user_id: UUID,
    *,
    fallback_summary: str | None,
    update_metadata: bool,
) -> tuple[str, str, str | None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        document_service = create_document_service(session)
        entries = await document_service.get_conversation_document_summaries(
            conversation_id,
            user_id=user_id,
        )

    documents_summary = await ConversationDocumentsSummarizer().synthesize(entries)
    if documents_summary is None:
        documents_summary = fallback_summary

    async with session_factory() as session:
        memory_service = create_conversation_memory_service(session)
        conversation_service = create_conversation_service(session)
        await memory_service.upsert_documents_summary(
            conversation_id,
            documents_summary,
        )
        if update_metadata and documents_summary:
            title, topic = await conversation_service.update_from_summary(
                conversation_id,
                documents_summary,
                user_id=user_id,
            )
            return title, topic, documents_summary

        conversation = await conversation_service.get_conversation(
            conversation_id,
            user_id=user_id,
        )
        return (
            conversation.title or "New Conversation",
            conversation.topic or "general",
            documents_summary,
        )
