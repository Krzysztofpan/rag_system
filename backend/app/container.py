from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.ingest.queue import IngestQueue
from app.lib.redis import get_redis
from app.services.chat.redis_run_registry import RedisRunRegistry
from app.services.conversation_events import ConversationEventBroker
from app.services.conversation_service import ConversationService
from app.services.conversation_memory_service import ConversationMemoryService
from app.services.document_service import DocumentService
from app.services.resource_service import ResourceService
from app.services.usage_limits import UsageLimitService
from app.services.vector_store import VectorStore
from app.services.message_service import MessageService

_vector_store: VectorStore | None = None
_run_registry: RedisRunRegistry | None = None
_conversation_event_broker: ConversationEventBroker | None = None
_ingest_queue: IngestQueue | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def get_run_registry() -> RedisRunRegistry:
    global _run_registry
    if _run_registry is None:
        _run_registry = RedisRunRegistry(get_redis())
    return _run_registry


def get_conversation_event_broker() -> ConversationEventBroker:
    global _conversation_event_broker
    if _conversation_event_broker is None:
        _conversation_event_broker = ConversationEventBroker(get_redis())
    return _conversation_event_broker


def get_ingest_queue() -> IngestQueue:
    global _ingest_queue
    if _ingest_queue is None:
        _ingest_queue = IngestQueue(get_redis())
    return _ingest_queue


def create_document_service(
    session: AsyncSession,
    vector_store: VectorStore | None = None,
) -> DocumentService:
    return DocumentService(
        session,
        vector_store or get_vector_store(),
    )


def get_document_service(
    session: AsyncSession = Depends(get_session),
    vector_store: VectorStore = Depends(get_vector_store),
) -> DocumentService:
    return create_document_service(session, vector_store)


def create_conversation_service(
    session: AsyncSession,
    vector_store: VectorStore | None = None,
) -> ConversationService:
    return ConversationService(
        session,
        vector_store or get_vector_store(),
    )


def get_conversation_service(
    session: AsyncSession = Depends(get_session),
    vector_store: VectorStore = Depends(get_vector_store),
) -> ConversationService:
    return create_conversation_service(session, vector_store)


def create_resource_service(
    session: AsyncSession,
) -> ResourceService:
    return ResourceService(session)


def get_resource_service(
    session: AsyncSession = Depends(get_session),
) -> ResourceService:
    return create_resource_service(session)


def create_message_service(
    session: AsyncSession,
) -> MessageService:
    return MessageService(session)

def get_message_service(
    session: AsyncSession = Depends(get_session),
) -> MessageService:
    return create_message_service(session)


def create_usage_limit_service(
    session: AsyncSession,
) -> UsageLimitService:
    return UsageLimitService(session)


def get_usage_limit_service(
    session: AsyncSession = Depends(get_session),
) -> UsageLimitService:
    return create_usage_limit_service(session)


def create_conversation_memory_service(
    session: AsyncSession,
    conversation_service: ConversationService | None = None,
    message_service: MessageService | None = None,
) -> ConversationMemoryService:
    return ConversationMemoryService(
        session,
        conversation_service or create_conversation_service(session),
        message_service or create_message_service(session),
    )


def get_conversation_memory_service(
    session: AsyncSession = Depends(get_session),
    conversation_service: ConversationService = Depends(get_conversation_service),
    message_service: MessageService = Depends(get_message_service),
) -> ConversationMemoryService:
    return create_conversation_memory_service(
        session,
        conversation_service,
        message_service,
    )