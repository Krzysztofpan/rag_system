from uuid import UUID

from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec

from app.config import get_settings
from app.services.chunker import ChunkResult

settings = get_settings()
pc = Pinecone(api_key=settings.pinecone_api_key)


class VectorStore:
    def __init__(
        self,
        embedder: OpenAIEmbeddings | None = None,
    ):
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
        self.vector_index = pc.index(settings.pinecone_index)
        self.embedder = embedder or OpenAIEmbeddings(model=settings.embedding_model)

    def add_vectors(self, vectors, *, conversation_id: UUID):
        self.vector_index.upsert(
            vectors=vectors,
            namespace=str(conversation_id),
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
