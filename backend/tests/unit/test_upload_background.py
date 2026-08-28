from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.background_tasks.upload_background import (
    apply_document_summary,
    refresh_and_publish_documents_summary,
)


def _session_factory():
    session = MagicMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=session_cm), session


async def test_apply_document_summary_stores_catalog_and_updates_metadata():
    conversation_id = uuid4()
    document_id = uuid4()
    user_id = uuid4()

    indexing_service = MagicMock()
    indexing_service.summarize_document = AsyncMock(return_value="A short summary")
    conversation_service = MagicMock()
    conversation_service.update_from_summary = AsyncMock(
        return_value=("Contracts and invoices", "finance")
    )
    memory_service = MagicMock()
    memory_service.upsert_documents_summary = AsyncMock()
    document_service = MagicMock()
    document_service.get_conversation_document_summaries = AsyncMock(
        return_value=[("invoices.md", "A short summary")]
    )
    broker = MagicMock()
    broker.publish = AsyncMock()
    session_factory, _session = _session_factory()

    with (
        patch(
            "app.background_tasks.upload_background.DocumentIndexingService",
            return_value=indexing_service,
        ),
        patch(
            "app.background_tasks.upload_background.get_session_factory",
            return_value=session_factory,
        ),
        patch(
            "app.background_tasks.upload_background.create_conversation_service",
            return_value=conversation_service,
        ),
        patch(
            "app.background_tasks.upload_background.create_conversation_memory_service",
            return_value=memory_service,
        ),
        patch(
            "app.background_tasks.upload_background.create_document_service",
            return_value=document_service,
        ),
        patch(
            "app.background_tasks.upload_background.get_conversation_event_broker",
            return_value=broker,
        ),
        patch(
            "app.background_tasks.upload_background.ConversationDocumentsSummarizer.synthesize",
            new=AsyncMock(return_value="Catalog of invoices"),
        ),
    ):
        await apply_document_summary(
            "# Doc",
            conversation_id,
            document_id,
            user_id,
        )

    indexing_service.summarize_document.assert_awaited_once_with(
        "# Doc",
        conversation_id,
        document_id,
        user_id,
    )
    document_service.get_conversation_document_summaries.assert_awaited_once_with(
        conversation_id,
        user_id=user_id,
    )
    memory_service.upsert_documents_summary.assert_awaited_once_with(
        conversation_id,
        "Catalog of invoices",
    )
    conversation_service.update_from_summary.assert_awaited_once_with(
        conversation_id,
        "Catalog of invoices",
        user_id=user_id,
    )
    broker.publish.assert_awaited_once_with(
        conversation_id,
        {
            "event": "conversation.updated",
            "conversationId": str(conversation_id),
            "title": "Contracts and invoices",
            "topic": "finance",
            "documentsSummary": "Catalog of invoices",
        },
    )


async def test_refresh_and_publish_documents_summary_skips_title_update():
    conversation_id = uuid4()
    user_id = uuid4()
    conversation_service = MagicMock()
    conversation_service.get_conversation = AsyncMock(
        return_value=MagicMock(title="Go notes", topic="tech")
    )
    memory_service = MagicMock()
    memory_service.upsert_documents_summary = AsyncMock()
    document_service = MagicMock()
    document_service.get_conversation_document_summaries = AsyncMock(
        return_value=[]
    )
    broker = MagicMock()
    broker.publish = AsyncMock()
    session_factory, _session = _session_factory()

    with (
        patch(
            "app.background_tasks.upload_background.get_session_factory",
            return_value=session_factory,
        ),
        patch(
            "app.background_tasks.upload_background.create_conversation_service",
            return_value=conversation_service,
        ),
        patch(
            "app.background_tasks.upload_background.create_conversation_memory_service",
            return_value=memory_service,
        ),
        patch(
            "app.background_tasks.upload_background.create_document_service",
            return_value=document_service,
        ),
        patch(
            "app.background_tasks.upload_background.get_conversation_event_broker",
            return_value=broker,
        ),
        patch(
            "app.background_tasks.upload_background.ConversationDocumentsSummarizer.synthesize",
            new=AsyncMock(return_value=None),
        ),
    ):
        await refresh_and_publish_documents_summary(conversation_id, user_id)

    conversation_service.update_from_summary.assert_not_called()
    memory_service.upsert_documents_summary.assert_awaited_once_with(
        conversation_id,
        None,
    )
    broker.publish.assert_awaited_once_with(
        conversation_id,
        {
            "event": "conversation.updated",
            "conversationId": str(conversation_id),
            "title": "Go notes",
            "topic": "tech",
            "documentsSummary": None,
        },
    )
