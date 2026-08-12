from typing import Optional
from uuid import UUID

from langchain.tools import ToolRuntime, tool

from app.container import get_vector_store
from app.db.session import get_session_factory
from app.graphs.search_documents_graph import SearchDocumentsGraph
from app.services.fts_retriever import PostgresFTSRetriever


@tool
def search_documents(
    query: str,
    top_k: int,
    runtime: ToolRuntime,
) -> str:
    """
    Search info from documents in conversation context

    Args:
    query: The search query. informations that user's looking for.
    top_k: Amount of chunks relevant to retrive to answer a user question, more complicated question more amount of chunks
 
    Return Value:
    Context from documents with metadata, and source to context.
    """
    conversation_id = runtime.context["conversation_id"]
    session_factory = get_session_factory()
    fts_retriever = PostgresFTSRetriever(
        session_factory=session_factory,
        k=top_k,
        conversation_id=conversation_id,
    )
    vector_store_retriever = get_vector_store().get_retriever(
        conversation_id=str(conversation_id),
        k=top_k,
        session_factory=session_factory,
    )
    search_documents_pipeline = SearchDocumentsGraph(
        fts_retriever=fts_retriever,
        vector_store_retriever=vector_store_retriever,
    ).build_graph()

    try:
        graph_res = search_documents_pipeline.invoke({
            "query": query,
            "search_retry_count": 0,
        })
    except Exception:
        raise SystemError("Error during running graph")

    return graph_res["context"]

