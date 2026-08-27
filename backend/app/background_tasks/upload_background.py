from uuid import UUID

from app.container import create_conversation_service, get_conversation_event_broker
from app.db.session import get_session_factory
from app.lib.tracing import conversation_tracing
from app.services.chunker.factory import ChunkerFactory
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
        summary = await indexing_service.summarize_document(
            parsed_content,
            conversation_id,
            document_id,
            user_id,
        )

        session_factory = get_session_factory()
        async with session_factory() as session:
            conversation_service = create_conversation_service(session)
            title, topic = await conversation_service.update_from_summary(
                conversation_id,
                summary,
                user_id=user_id,
            )

        await get_conversation_event_broker().publish(
            conversation_id,
            conversation_updated_event(conversation_id, title, topic),
        )
