from __future__ import annotations

from uuid import UUID

from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.chunk import Chunk
from app.db.models.document import Document as DbDocument
from app.db.session import run_async


class PostgresFTSRetriever(BaseRetriever):
    """Minimal BaseRetriever over chunks.search_vector for EnsembleRetriever."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    session_factory: async_sessionmaker[AsyncSession]
    k: int
    conversation_id: UUID | None = None
    document_ids: list[UUID] | None = None

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        # EnsembleRetriever.invoke() path; prefer ainvoke() in async code.
        return run_async(self._search(query))

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        return await self._search(query)

    async def _search(self, query: str) -> list[Document]:
        if not query.strip() or not self.document_ids:
            return []

        ts_query = func.plainto_tsquery("simple", query)
        rank = func.ts_rank(Chunk.search_vector, ts_query)
        stmt = (
            select(Chunk, rank.label("rank"))
            .join(DbDocument, DbDocument.id == Chunk.document_id)
            .where(
                Chunk.search_vector.op("@@")(ts_query),
                Chunk.document_id.in_(self.document_ids),
            )
            .order_by(rank.desc())
            .limit(self.k)
        )

        if self.conversation_id is not None:
            stmt = stmt.where(DbDocument.conversation_id == self.conversation_id)

        async with self.session_factory() as session:
            rows = (await session.execute(stmt)).all()

        return [
            Document(
                page_content=chunk.content,
                metadata={
                    "chunk_id": str(chunk.id),
                    "document_id": str(chunk.document_id),
                    "chunk_index": chunk.chunk_index,
                    "context": chunk.context,
                    "pages": chunk.pages,
                    "score": float(score) if score is not None else None,
                },
            )
            for chunk, score in rows
        ]
