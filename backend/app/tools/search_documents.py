from langchain.tools import ToolRuntime, tool

from app.agent.types import AgentContext
from app.container import get_vector_store
from app.db.session import get_session_factory
from app.graphs.search_documents_graph import SearchDocumentsGraph
from app.services.document_service import DocumentService
from app.services.fts_retriever import PostgresFTSRetriever


@tool
async def search_documents(
    query: str,
    top_k: int,
    runtime: ToolRuntime[AgentContext],
) -> str:
    """
    Search the documents already selected for this conversation.

    Args:
    query: The search query. informations that user's looking for.
    top_k: Amount of chunks relevant to retrive to answer a user question, more complicated question more amount of chunks

    Selected document IDs are provided by the application — do not ask the user for them.

    Return Value:
    Context from documents with metadata, and source to context.
    """
    document_ids = runtime.context["document_ids"]
    conversation_id = runtime.context["conversation_id"]
    user_id = runtime.context["user_id"]

    session_factory = get_session_factory()

    async with session_factory() as session:
        store = DocumentService(session)
        await store.get_documents(
            conversation_id,
            document_ids,
            user_id=user_id,
        )

    if not document_ids:
        return "no context founded"

    fts_retriever = PostgresFTSRetriever(
        session_factory=session_factory,
        k=top_k,
        conversation_id=conversation_id,
        document_ids=document_ids,
    )

    vector_store_retriever = get_vector_store().get_retriever(
        conversation_id=str(conversation_id),
        k=top_k,
        session_factory=session_factory,
        document_ids=document_ids,
    )

    search_documents_pipeline = SearchDocumentsGraph(
        fts_retriever=fts_retriever,
        vector_store_retriever=vector_store_retriever,
    ).build_graph()

    try:
        graph_res = await search_documents_pipeline.ainvoke({
            "query": query,
            "search_retry_count": 0,
        })
    except Exception:
        raise SystemError("Error during running graph")

    return graph_res["context"]
