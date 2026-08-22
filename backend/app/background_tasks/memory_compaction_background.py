import logging
from uuid import UUID

from app.container import create_conversation_memory_service
from app.db.session import get_session_factory
from app.lib.tracing import conversation_tracing

logger = logging.getLogger(__name__)


async def compact_conversation_memory(
    conversation_id: UUID,
    user_id: UUID,
) -> None:
    with conversation_tracing(
        conversation_id,
        user_id=user_id,
        tags=["memory"],
    ):
        session_factory = get_session_factory()
        async with session_factory() as session:
            service = create_conversation_memory_service(session)
            try:
                await service.compact_if_needed(
                    conversation_id,
                    user_id=user_id,
                )
            except Exception:
                logger.exception(
                    "Conversation memory compaction failed",
                    extra={"conversation_id": str(conversation_id)},
                )
