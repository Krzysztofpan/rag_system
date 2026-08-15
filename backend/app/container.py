from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.chunker.factory import ChunkerFactory
from app.services.conversation_service import ConversationService
from app.services.doc_store import DocumentStore
from app.services.document_indexing_service import DocumentIndexingService
from app.services.parser.factory import ParserFactory
from app.services.vector_store import VectorStore

_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def create_indexing_service(
    session: AsyncSession,
    vector_store: VectorStore | None = None,
) -> DocumentIndexingService:
    return DocumentIndexingService(
        parser_factory=ParserFactory(),
        chunker_factory=ChunkerFactory(),
        doc_store=DocumentStore(session),
        vector_store=vector_store or get_vector_store(),
    )


def get_document_indexing_service(
    session: AsyncSession = Depends(get_session),
    vector_store: VectorStore = Depends(get_vector_store),
) -> DocumentIndexingService:
    return create_indexing_service(session, vector_store)


def create_conversation_service(
    session: AsyncSession,
    vector_store: VectorStore | None = None,
) -> ConversationService:
    return ConversationService(
        session,
        vector_store or get_vector_store(),
        DocumentStore(session),
    )


def get_conversation_service(
    session: AsyncSession = Depends(get_session),
    vector_store: VectorStore = Depends(get_vector_store),
) -> ConversationService:
    return create_conversation_service(session, vector_store)
