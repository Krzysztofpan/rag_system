from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.services.vector_store import VectorStore
from tests.helpers import make_chunk


def test_text_for_embedding_without_context():
    chunk = make_chunk("body only")
    assert VectorStore.text_for_embedding(chunk) == "body only"


def test_text_for_embedding_with_context():
    chunk = make_chunk("body", context="Heading / Section")
    assert VectorStore.text_for_embedding(chunk) == "Heading / Section\n\nbody"


def test_construct_vectors_builds_pinecone_records():
    store = VectorStore.__new__(VectorStore)
    store.embed_texts = MagicMock(return_value=[[0.1, 0.2], [0.3, 0.4]])

    chunk_id_1, chunk_id_2 = uuid4(), uuid4()
    document_id = uuid4()
    stored = [
        (chunk_id_1, make_chunk("first", context="Ctx", pages=[1, 2])),
        (chunk_id_2, make_chunk("second")),
    ]

    vectors = store.construct_vectors(
        stored,
        document_id=document_id,
        source_filename="doc.pdf",
    )

    store.embed_texts.assert_called_once_with(["Ctx\n\nfirst", "second"])
    assert vectors[0]["id"] == str(chunk_id_1)
    assert vectors[0]["values"] == [0.1, 0.2]
    assert vectors[0]["metadata"] == {
        "document_id": str(document_id),
        "chunk_index": 0,
        "source_filename": "doc.pdf",
        "pages": ["1", "2"],
    }
    assert "pages" not in vectors[1]["metadata"]
    assert vectors[1]["metadata"]["chunk_index"] == 1


def test_add_vectors_upserts_into_conversation_namespace():
    store = VectorStore.__new__(VectorStore)
    store.vector_index = MagicMock()
    conversation_id = uuid4()
    vectors = [{"id": "a", "values": [1.0]}]

    store.add_vectors(vectors, conversation_id=conversation_id)

    store.vector_index.upsert.assert_called_once_with(
        vectors=vectors,
        namespace=str(conversation_id),
    )


def test_delete_namespace_deletes_all_in_conversation():
    store = VectorStore.__new__(VectorStore)
    store.vector_index = MagicMock()
    conversation_id = uuid4()

    store.delete_namespace(conversation_id)

    store.vector_index.delete.assert_called_once_with(
        delete_all=True,
        namespace=str(conversation_id),
    )


def test_delete_document_vectors_filters_by_document_id():
    store = VectorStore.__new__(VectorStore)
    store.vector_index = MagicMock()
    conversation_id = uuid4()
    document_id = uuid4()

    store.delete_document_vectors(conversation_id, document_id)

    store.vector_index.delete.assert_called_once_with(
        namespace=str(conversation_id),
        filter={"document_id": {"$eq": str(document_id)}},
    )


def test_update_document_source_filename_filters_by_document_id():
    store = VectorStore.__new__(VectorStore)
    store.vector_index = MagicMock()
    conversation_id = uuid4()
    document_id = uuid4()

    store.update_document_source_filename(
        conversation_id,
        document_id,
        "renamed.pdf",
    )

    store.vector_index.update.assert_called_once_with(
        namespace=str(conversation_id),
        filter={"document_id": {"$eq": str(document_id)}},
        set_metadata={"source_filename": "renamed.pdf"},
    )


def test_get_retriever_passes_document_ids():
    store = VectorStore.__new__(VectorStore)
    store.vector_index = MagicMock()
    store.embedder = MagicMock()
    conversation_id = uuid4()
    document_ids = [uuid4(), uuid4()]
    session_factory = MagicMock()

    with patch(
        "app.services.vector_store.HydratedPineconeRetriever"
    ) as retriever_cls:
        store.get_retriever(
            str(conversation_id),
            k=7,
            session_factory=session_factory,
            document_ids=document_ids,
        )

    retriever_cls.assert_called_once_with(
        index=store.vector_index,
        embedder=store.embedder,
        session_factory=session_factory,
        conversation_id=str(conversation_id),
        k=7,
        document_ids=document_ids,
    )
