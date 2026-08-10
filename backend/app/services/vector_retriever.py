from __future__ import annotations

from typing import Any
from uuid import UUID

from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.chunk import Chunk
from app.db.session import run_async


class HydratedPineconeRetriever(BaseRetriever):
    """Pinecone similarity search with chunk text loaded from Postgres."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    index: Any
    embedder: Embeddings
    session_factory: async_sessionmaker[AsyncSession]
    conversation_id: str
    k: int
    document_id: UUID | None = None

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        return run_async(self._search(query))

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        return await self._search(query)

    async def _search(self, query: str) -> list[Document]:
        if not query.strip():
            return []

        embedding = await self.embedder.aembed_query(query)
        filter = (
            {"document_id": {"$eq": str(self.document_id)}}
            if self.document_id is not None
            else None
        )
        results = self.index.query(
            vector=embedding,
            top_k=self.k,
            include_metadata=True,
            namespace=self.conversation_id,
            filter=filter,
        )
        matches = results.get("matches") or []
        if not matches:
            return []

        chunk_ids: list[UUID] = []
        ordered_ids: list[str] = []
        scores: dict[str, float | None] = {}
        for match in matches:
            match_id = match.get("id")
            if not match_id:
                continue
            try:
                chunk_ids.append(UUID(match_id))
            except ValueError:
                continue
            ordered_ids.append(match_id)
            score = match.get("score")
            scores[match_id] = float(score) if score is not None else None

        if not chunk_ids:
            return []

        async with self.session_factory() as session:
            rows = (
                await session.execute(select(Chunk).where(Chunk.id.in_(chunk_ids)))
            ).scalars().all()

        by_id = {str(chunk.id): chunk for chunk in rows}
        docs: list[Document] = []
        for chunk_id in ordered_ids:
            chunk = by_id.get(chunk_id)
            if chunk is None:
                continue
            docs.append(
                Document(
                    page_content=chunk.content,
                    metadata={
                        "chunk_id": str(chunk.id),
                        "document_id": str(chunk.document_id),
                        "chunk_index": chunk.chunk_index,
                        "context": chunk.context,
                        "pages": chunk.pages,
                        "score": scores.get(chunk_id),
                    },
                )
            )
        return docs
