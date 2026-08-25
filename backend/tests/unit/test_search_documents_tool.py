from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langchain_core.documents import Document

from app.tools.search_documents import search_documents


def _runtime(*, conversation_id=None, user_id=None, document_ids=None, config=None):
    return SimpleNamespace(
        context={
            "conversation_id": conversation_id or uuid4(),
            "user_id": user_id or uuid4(),
            "document_ids": document_ids if document_ids is not None else [uuid4()],
            "sources": [],
        },
        config=config,
    )


def _session_factory():
    session = MagicMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=session_cm)


def test_llm_schema_hides_runtime_and_scoped_ids():
    schema = search_documents.tool_call_schema.model_json_schema()
    properties = schema.get("properties", {})

    assert "conversation_id" not in properties
    assert "user_id" not in properties
    assert "document_ids" not in properties
    assert "runtime" not in properties
    assert "query" in properties
    assert "top_k" in properties


@patch("app.tools.search_documents.DocumentService")
@patch("app.tools.search_documents.get_session_factory")
@patch("app.tools.search_documents.PostgresFTSRetriever")
@patch("app.tools.search_documents.get_vector_store")
@patch("app.tools.search_documents.SearchDocumentsGraph")
async def test_search_documents_scopes_to_owned_document_ids(
    graph_cls,
    get_vector_store,
    fts_cls,
    get_session_factory,
    store_cls,
):
    conversation_id = uuid4()
    user_id = uuid4()
    document_ids = [uuid4(), uuid4()]
    runtime = _runtime(
        conversation_id=conversation_id,
        user_id=user_id,
        document_ids=document_ids,
    )
    summary_document_id = uuid4()
    runtime.context["sources"].append(
        {
            "index": 1,
            "kind": "summary",
            "document_id": str(summary_document_id),
        }
    )
    get_session_factory.return_value = _session_factory()
    store = MagicMock()
    store.get_documents = AsyncMock(
        return_value=[
            SimpleNamespace(id=document_ids[0], filename="stack.md"),
            SimpleNamespace(id=document_ids[1], filename="other.md"),
        ]
    )
    store_cls.return_value = store
    get_vector_store.return_value.get_retriever.return_value = MagicMock()
    graph_cls.return_value.build_graph.return_value.ainvoke = AsyncMock(
        return_value={
            "relevant_docs": [
                Document(
                    page_content="found stack",
                    metadata={
                        "chunk_id": "a",
                        "document_id": str(document_ids[0]),
                    },
                )
            ],
        }
    )

    result = await search_documents.coroutine(
        query="frontend stack",
        top_k=5,
        runtime=runtime,
    )

    assert result.startswith("[2] stack.md")
    assert "found stack" in result
    assert runtime.context["sources"] == [
        {
            "index": 1,
            "kind": "summary",
            "document_id": str(summary_document_id),
        },
        {"index": 2, "kind": "chunk", "chunk_id": "a"},
    ]
    store.get_documents.assert_awaited_once_with(
        conversation_id,
        document_ids,
        user_id=user_id,
    )
    graph_cls.return_value.build_graph.return_value.ainvoke.assert_awaited_once_with(
        {
            "query": "frontend stack",
            "user_query": "frontend stack",
            "search_retry_count": 0,
        },
        config={"run_name": "search_documents"},
    )
    assert fts_cls.call_args.kwargs["conversation_id"] == conversation_id
    assert fts_cls.call_args.kwargs["document_ids"] == document_ids
    retriever_kwargs = get_vector_store.return_value.get_retriever.call_args.kwargs
    assert retriever_kwargs["conversation_id"] == str(conversation_id)
    assert retriever_kwargs["document_ids"] == document_ids


@patch("app.tools.search_documents.DocumentService")
@patch("app.tools.search_documents.get_session_factory")
@patch("app.tools.search_documents.PostgresFTSRetriever")
@patch("app.tools.search_documents.get_vector_store")
@patch("app.tools.search_documents.SearchDocumentsGraph")
async def test_search_documents_skips_search_when_no_document_ids(
    graph_cls,
    get_vector_store,
    fts_cls,
    get_session_factory,
    store_cls,
):
    conversation_id = uuid4()
    user_id = uuid4()
    runtime = _runtime(
        conversation_id=conversation_id,
        user_id=user_id,
        document_ids=[],
    )
    get_session_factory.return_value = _session_factory()
    store = MagicMock()
    store.get_documents = AsyncMock(return_value=[])
    store_cls.return_value = store

    result = await search_documents.coroutine(
        query="frontend stack", top_k=5, runtime=runtime
    )

    assert result == "no context founded"
    get_session_factory.assert_not_called()
    store.get_documents.assert_not_awaited()
    fts_cls.assert_not_called()
    get_vector_store.return_value.get_retriever.assert_not_called()
    graph_cls.assert_not_called()


@patch("app.tools.search_documents.DocumentService")
@patch("app.tools.search_documents.get_session_factory")
@patch("app.tools.search_documents.PostgresFTSRetriever")
@patch("app.tools.search_documents.get_vector_store")
@patch("app.tools.search_documents.SearchDocumentsGraph")
async def test_search_documents_returns_no_context_when_graph_finds_nothing(
    graph_cls,
    get_vector_store,
    fts_cls,
    get_session_factory,
    store_cls,
):
    runtime = _runtime()
    get_session_factory.return_value = _session_factory()
    store = MagicMock()
    store.get_documents = AsyncMock(return_value=[])
    store_cls.return_value = store
    get_vector_store.return_value.get_retriever.return_value = MagicMock()
    graph_cls.return_value.build_graph.return_value.ainvoke = AsyncMock(
        return_value={"relevant_docs": []}
    )

    result = await search_documents.coroutine(
        query="frontend stack", top_k=5, runtime=runtime
    )

    assert result == "no context founded"


@patch("app.tools.search_documents.DocumentService")
@patch("app.tools.search_documents.get_session_factory")
@patch("app.tools.search_documents.SearchDocumentsGraph")
async def test_search_documents_rejects_unowned_conversation(
    graph_cls,
    get_session_factory,
    store_cls,
):
    runtime = _runtime()
    get_session_factory.return_value = _session_factory()
    store = MagicMock()
    store.get_documents = AsyncMock(
        side_effect=ValueError("Conversation missing not found")
    )
    store_cls.return_value = store

    with pytest.raises(ValueError, match="not found"):
        await search_documents.coroutine(
            query="frontend stack", top_k=5, runtime=runtime
        )

    graph_cls.assert_not_called()


@patch("app.tools.search_documents.DocumentService")
@patch("app.tools.search_documents.get_session_factory")
@patch("app.tools.search_documents.PostgresFTSRetriever")
@patch("app.tools.search_documents.get_vector_store")
@patch("app.tools.search_documents.SearchDocumentsGraph")
async def test_search_documents_propagates_graph_errors(
    graph_cls,
    get_vector_store,
    fts_cls,
    get_session_factory,
    store_cls,
):
    runtime = _runtime()
    get_session_factory.return_value = _session_factory()
    store = MagicMock()
    store.get_documents = AsyncMock(return_value=[])
    store_cls.return_value = store
    get_vector_store.return_value.get_retriever.return_value = MagicMock()
    graph_cls.return_value.build_graph.return_value.ainvoke = AsyncMock(
        side_effect=RuntimeError("COHERE_API_KEY is not configured")
    )

    with pytest.raises(RuntimeError, match="COHERE_API_KEY"):
        await search_documents.coroutine(
            query="frontend stack", top_k=5, runtime=runtime
        )


@patch("app.tools.search_documents.DocumentService")
@patch("app.tools.search_documents.get_session_factory")
@patch("app.tools.search_documents.PostgresFTSRetriever")
@patch("app.tools.search_documents.get_vector_store")
@patch("app.tools.search_documents.SearchDocumentsGraph")
async def test_search_documents_does_not_inherit_agent_runnable_config(
    graph_cls,
    get_vector_store,
    fts_cls,
    get_session_factory,
    store_cls,
):
    conversation_id = uuid4()
    user_id = uuid4()
    runtime = _runtime(
        conversation_id=conversation_id,
        user_id=user_id,
        config={
            "callbacks": ["parent-callback"],
            "tags": ["chat"],
            "configurable": {"checkpoint_ns": "tools:nested"},
        },
    )
    get_session_factory.return_value = _session_factory()
    store = MagicMock()
    store.get_documents = AsyncMock(return_value=[])
    store_cls.return_value = store
    get_vector_store.return_value.get_retriever.return_value = MagicMock()
    graph_cls.return_value.build_graph.return_value.ainvoke = AsyncMock(
        return_value={"relevant_docs": [Document(page_content="found stack")]}
    )

    await search_documents.coroutine(
        query="frontend stack",
        top_k=5,
        runtime=runtime,
    )

    config = graph_cls.return_value.build_graph.return_value.ainvoke.await_args.kwargs[
        "config"
    ]
    assert config == {"run_name": "search_documents"}
    assert "callbacks" not in config
