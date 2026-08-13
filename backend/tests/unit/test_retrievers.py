from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.fts_retriever import PostgresFTSRetriever
from app.services.vector_retriever import HydratedPineconeRetriever


async def test_fts_retriever_returns_empty_without_document_ids():
    session_factory = MagicMock()
    retriever = PostgresFTSRetriever.model_construct(
        session_factory=session_factory,
        k=5,
        conversation_id=uuid4(),
        document_ids=[],
    )

    assert await retriever._search("frontend stack") == []
    session_factory.assert_not_called()


async def test_fts_retriever_filters_by_document_ids_and_conversation():
    conversation_id = uuid4()
    document_ids = [uuid4(), uuid4()]
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    session_factory = MagicMock(return_value=session_cm)

    retriever = PostgresFTSRetriever.model_construct(
        session_factory=session_factory,
        k=5,
        conversation_id=conversation_id,
        document_ids=document_ids,
    )

    assert await retriever._search("frontend stack") == []

    statement = session.execute.await_args.args[0]
    compiled = str(statement.compile()).lower()
    assert "document_id" in compiled
    assert "conversation_id" in compiled
    assert " in (" in compiled or "in(" in compiled


async def test_vector_retriever_returns_empty_without_document_ids():
    embedder = MagicMock()
    embedder.aembed_query = AsyncMock()
    index = MagicMock()
    retriever = HydratedPineconeRetriever.model_construct(
        index=index,
        embedder=embedder,
        session_factory=MagicMock(),
        conversation_id=str(uuid4()),
        k=5,
        document_ids=[],
    )

    assert await retriever._search("frontend stack") == []
    embedder.aembed_query.assert_not_awaited()
    index.query.assert_not_called()


async def test_vector_retriever_filters_pinecone_query_by_document_ids():
    conversation_id = uuid4()
    document_ids = [uuid4(), uuid4()]
    embedder = MagicMock()
    embedder.aembed_query = AsyncMock(return_value=[0.1, 0.2])
    index = MagicMock()
    index.query.return_value = {"matches": []}
    retriever = HydratedPineconeRetriever.model_construct(
        index=index,
        embedder=embedder,
        session_factory=MagicMock(),
        conversation_id=str(conversation_id),
        k=5,
        document_ids=document_ids,
    )

    assert await retriever._search("frontend stack") == []

    index.query.assert_called_once_with(
        vector=[0.1, 0.2],
        top_k=5,
        include_metadata=True,
        namespace=str(conversation_id),
        filter={"document_id": {"$in": [str(document_ids[0]), str(document_ids[1])]}},
    )
