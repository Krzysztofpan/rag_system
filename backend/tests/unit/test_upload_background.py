from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.background_tasks.upload_background import summarize_document_and_update_title


async def test_summarize_document_and_update_title_chains_existing_methods():
    conversation_id = uuid4()
    document_id = uuid4()
    user_id = uuid4()

    indexing_service = MagicMock()
    indexing_service.summarize_document = AsyncMock(return_value="A short summary")
    conversation_service = MagicMock()
    conversation_service.generate_conversation_title = AsyncMock(
        return_value="Contracts and invoices"
    )
    broker = MagicMock()
    broker.publish = AsyncMock()

    session = MagicMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    session_factory = MagicMock(return_value=session_cm)

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
        ) as create_conversation,
        patch(
            "app.background_tasks.upload_background.get_conversation_event_broker",
            return_value=broker,
        ),
    ):
        await summarize_document_and_update_title(
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
    create_conversation.assert_called_once_with(session)
    conversation_service.generate_conversation_title.assert_awaited_once_with(
        conversation_id,
        "A short summary",
        user_id=user_id,
    )
    broker.publish.assert_awaited_once_with(
        conversation_id,
        {
            "event": "conversation.title",
            "conversationId": str(conversation_id),
            "title": "Contracts and invoices",
        },
    )
