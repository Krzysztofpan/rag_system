from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.chunker.factory import ChunkerFactory
from app.services.chat.run_registry import InMemoryRunRegistry
from app.services.conversation_events import ConversationEventBroker
from app.services.conversation_service import ConversationService
from app.services.conversation_memory_service import ConversationMemoryService
from app.services.document_service import DocumentService
from app.services.document_indexing_service import DocumentIndexingService
from app.services.parser.factory import ParserFactory
from app.services.usage_limits import UsageLimitService
from app.services.vector_store import VectorStore
from app.services.message_service import MessageService

_vector_store: VectorStore | None = None
_run_registry: InMemoryRunRegistry | None = None
_conversation_event_broker: ConversationEventBroker | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def get_run_registry() -> InMemoryRunRegistry:
    global _run_registry
    if _run_registry is None:
        _run_registry = InMemoryRunRegistry()
    return _run_registry


def get_conversation_event_broker() -> ConversationEventBroker:
    global _conversation_event_broker
    if _conversation_event_broker is None:
        _conversation_event_broker = ConversationEventBroker()
    return _conversation_event_broker


def create_indexing_service(
    session: AsyncSession,
    vector_store: VectorStore | None = None,
) -> DocumentIndexingService:
    return DocumentIndexingService(
        parser_factory=ParserFactory(),
        chunker_factory=ChunkerFactory(),
        document_service=DocumentService(session),
        vector_store=vector_store or get_vector_store(),
    )


def get_document_indexing_service(
    session: AsyncSession = Depends(get_session),
    vector_store: VectorStore = Depends(get_vector_store),
) -> DocumentIndexingService:
    return create_indexing_service(session, vector_store)


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