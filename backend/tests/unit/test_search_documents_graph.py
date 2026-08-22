from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from app.graphs.search_documents_graph import SearchDocumentsGraph, settings
from app.lib.cohere import get_cohere_client


def _graph() -> SearchDocumentsGraph:
    return SearchDocumentsGraph(
        fts_retriever=MagicMock(),
        vector_store_retriever=MagicMock(),
        llm_query_rewriter=MagicMock(),
    )


def _docs() -> list[Document]:
    return [
        Document(page_content="alpha", metadata={"chunk_id": "a"}),
        Document(page_content="beta", metadata={"chunk_id": "b"}),
        Document(page_content="gamma", metadata={"chunk_id": "c"}),
    ]


async def test_rerank_docs_skips_cohere_when_nothing_retrieved():
    pipeline = _graph()

    result = await pipeline.rerank_docs(
        {
            "query": "frontend stack",
            "retrieved_docs": [],
        }
    )

    assert result == {
        "relevant_docs": [],
        "doc_scores": [],
        "max_score": 0.0,
    }


@patch("app.graphs.search_documents_graph.get_cohere_client")
async def test_rerank_docs_orders_by_cohere_index_and_score(get_client):
    client = MagicMock()
    client.rerank = AsyncMock(
        return_value=SimpleNamespace(
            results=[
                SimpleNamespace(index=2, relevance_score=0.91),
                SimpleNamespace(index=0, relevance_score=0.44),
                SimpleNamespace(index=1, relevance_score=0.12),
            ]
        )
    )
    get_client.return_value = client
    docs = _docs()
    pipeline = _graph()

    result = await pipeline.rerank_docs(
        {
            "query": "frontend stack",
            "retrieved_docs": docs,
        }
    )

    client.rerank.assert_awaited_once_with(
        model=settings.cohere_rerank_model,
        query="frontend stack",
        documents=["alpha", "beta", "gamma"],
    )
    assert result["relevant_docs"] == [docs[2], docs[0], docs[1]]
    assert result["doc_scores"] == [0.91, 0.44, 0.12]
    assert result["max_score"] == 0.91


@patch("app.graphs.search_documents_graph.settings")
@patch("app.graphs.search_documents_graph.get_cohere_client")
async def test_rerank_docs_drops_hits_below_min_score(get_client, settings):
    settings.cohere_rerank_model = "rerank-v4.0-fast"
    settings.rerank_min_score = 0.5
    client = MagicMock()
    client.rerank = AsyncMock(
        return_value=SimpleNamespace(
            results=[
                SimpleNamespace(index=1, relevance_score=0.72),
                SimpleNamespace(index=0, relevance_score=0.31),
            ]
        )
    )
    get_client.return_value = client
    docs = _docs()[:2]
    pipeline = _graph()

    result = await pipeline.rerank_docs(
        {
            "query": "frontend stack",
            "retrieved_docs": docs,
        }
    )

    assert result["relevant_docs"] == [docs[1]]
    assert result["doc_scores"] == [0.72]
    assert result["max_score"] == 0.72


def test_route_rewrites_when_no_relevant_docs_on_first_try():
    pipeline = _graph()

    assert (
        pipeline.route_after_rerank_docs(
            {"relevant_docs": [], "search_retry_count": 0}
        )
        == "rewrite_query"
    )


def test_route_builds_context_after_hyde_even_if_still_empty():
    pipeline = _graph()

    assert (
        pipeline.route_after_rerank_docs(
            {"relevant_docs": [], "search_retry_count": 1}
        )
        == "build_context"
    )


@patch("app.lib.cohere.get_settings")
def test_get_cohere_client_requires_api_key(get_settings):
    get_cohere_client.cache_clear()
    get_settings.return_value = SimpleNamespace(cohere_api_key=None)

    with pytest.raises(RuntimeError, match="COHERE_API_KEY"):
        get_cohere_client()


def test_build_graph_is_named_search_documents():
    compiled = _graph().build_graph()

    assert compiled.name == "search_documents"
