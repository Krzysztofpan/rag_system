from sqlalchemy.ext.asyncio import AsyncSession

from app.container import get_vector_store
from app.services.chunker.factory import ChunkerFactory
from app.services.document_indexing_service import DocumentIndexingService
from app.services.document_service import DocumentService
from app.services.parser.factory import ParserFactory
from app.services.vector_store import VectorStore


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
