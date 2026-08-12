from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.agent.tools import search_documents


def test_llm_schema_hides_runtime_and_conversation_id():
    schema = search_documents.tool_call_schema.model_json_schema()
    properties = schema.get("properties", {})

    assert "conversation_id" not in properties
    assert "runtime" not in properties
    assert "query" in properties
    assert "top_k" in properties
    assert "doc_id" in properties


def test_search_documents_reads_conversation_id_from_runtime_context():
    conversation_id = uuid4()
    runtime = SimpleNamespace(context={"conversation_id": conversation_id})
    retriever = MagicMock()

    with (
        patch("app.agent.tools.get_session_factory", return_value=MagicMock()),
        patch("app.agent.tools.PostgresFTSRetriever") as fts_cls,
        patch("app.agent.tools.get_vector_store") as get_vector_store,
        patch("app.agent.tools.SearchDocumentsGraph") as graph_cls,
    ):
        get_vector_store.return_value.get_retriever.return_value = retriever
        graph_cls.return_value.build_graph.return_value.invoke.return_value = {
            "context": "found stack"
        }

        result = search_documents.func(
            query="frontend stack",
            top_k=5,
            runtime=runtime,
        )

    assert result == "found stack"
    fts_cls.assert_called_once()
    assert fts_cls.call_args.kwargs["conversation_id"] == conversation_id
    get_vector_store.return_value.get_retriever.assert_called_once()
    assert get_vector_store.return_value.get_retriever.call_args.kwargs[
        "conversation_id"
    ] == str(conversation_id)
