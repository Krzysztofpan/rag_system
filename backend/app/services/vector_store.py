from uuid import UUID

from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.services.chunker import ChunkResult
from app.services.vector_retriever import HydratedPineconeRetriever

settings = get_settings()


class VectorStore:
    def __init__(
        self,
        embedder: OpenAIEmbeddings | None = None,
    ):
        pc = Pinecone(api_key=settings.pinecone_api_key)
        if not pc.has_index(settings.pinecone_index):
            pc.create_index(
                name=settings.pinecone_index,
                vector_type="dense",
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
        self.vector_index = pc.Index(settings.pinecone_index)
        self.embedder = embedder or OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )

    def add_vectors(self, vectors, *, conversation_id: UUID):
        self.vector_index.upsert(
            vectors=vectors,
            namespace=str(conversation_id),
        )

    def delete_namespace(self, conversation_id: UUID) -> None:
        self.vector_index.delete(
            delete_all=True,
            namespace=str(conversation_id),
        )

    def delete_document_vectors(
        self,
        conversation_id: UUID,
        document_id: UUID,
    ) -> None:
        self.vector_index.delete(
            namespace=str(conversation_id),
            filter={"document_id": {"$eq": str(document_id)}},
        )

    def update_document_source_filename(
        self,
        conversation_id: UUID,
        document_id: UUID,
        source_filename: str,
    ) -> None:
        self.vector_index.update(
            namespace=str(conversation_id),
            filter={"document_id": {"$eq": str(document_id)}},
            set_metadata={"source_filename": source_filename},
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self.embedder.embed_documents(texts)

    @staticmethod
    def text_for_embedding(chunk: ChunkResult) -> str:
        if chunk.context:
            return f"{chunk.context}\n\n{chunk.content}"
        return chunk.content

    def construct_vectors(
        self,
        stored_chunks: list[tuple[UUID, ChunkResult]],
        *,
        document_id: UUID,
        source_filename: str,
    ) -> list[dict]:
        """Build Pinecone records: id = chunk UUID, metadata without text."""
        embeddings = self.embed_texts(
            [self.text_for_embedding(chunk) for _, chunk in stored_chunks]
        )

        vectors: list[dict] = []
        document_id_str = str(document_id)
        for chunk_index, ((chunk_id, chunk), values) in enumerate(
            zip(stored_chunks, embeddings)
        ):
            metadata: dict = {
                "document_id": document_id_str,
                "chunk_index": chunk_index,
                "source_filename": source_filename,
            }
            if chunk.pages is not None:
                # Pinecone allows list metadata only as list of strings.
                metadata["pages"] = [str(page) for page in chunk.pages]

            vectors.append(
                {
                    "id": str(chunk_id),
                    "values": values,
                    "metadata": metadata,
                }
            )
        return vectors

    def get_retriever(
        self,
        conversation_id: str,
        k: int,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        document_ids: list[UUID] | None = None,
    ) -> HydratedPineconeRetriever:
        return HydratedPineconeRetriever(
            index=self.vector_index,
            embedder=self.embedder,
            session_factory=session_factory,
            conversation_id=conversation_id,
            k=k,
            document_ids=document_ids,
        )
