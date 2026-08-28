import logging

from langchain.tools import ToolRuntime, tool

from app.agent.sources import cite_documents
from app.agent.types import AgentContext
from app.container import get_vector_store
from app.db.session import get_session_factory
from app.graphs.search_documents_graph import SearchDocumentsGraph
from app.lib.tracing import conversation_tracing
from app.services.document_service import DocumentService
from app.services.fts_retriever import PostgresFTSRetriever

logger = logging.getLogger(__name__)


@tool
async def search_documents(
    query: str,
    top_k: int,
    runtime: ToolRuntime[AgentContext],
) -> str:
    """
    Search the documents selected for this turn.

    Call this when the question could be answered from those selected files —
    articles, videos, transcripts, notes, policies, or any document facts.
    Do not skip this tool because the topic sounds like general knowledge
    or current events. Do not use it for uploaded files that are not selected.

    Args:
    query: The search query. informations that user's looking for.
    top_k: Amount of chunks relevant to retrive to answer a user question, more complicated question more amount of chunks

    Selected document IDs are provided by the application — do not ask the user for them.

    Return Value:
    Numbered document excerpts labeled [n]. Cite claims with those indices,
    or "no context founded".
    """
    document_ids = runtime.context["document_ids"]
    conversation_id = runtime.context["conversation_id"]
    user_id = runtime.context["user_id"]

    if not document_ids:
        return "no context founded"

    session_factory = get_session_factory()

    async with session_factory() as session:
        store = DocumentService(session)
        documents = await store.get_documents(
            conversation_id,
            document_ids,
            user_id=user_id,
        )

    filenames = {str(document.id): document.filename for document in documents}

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
        with conversation_tracing(
            conversation_id,
            user_id=user_id,
            tags=["retrieval"],
            as_root=True,
        ):
            graph_res = await search_documents_pipeline.ainvoke(
                {
                    "query": query,
                    # Prompt Shields needs the original user message, not the tool's rewritten query.
                    "user_query": runtime.context.get("user_query") or query,
                    "search_retry_count": 0,
                },
                config={"run_name": "search_documents"},
            )
    except Exception:
        logger.exception("search_documents graph failed")
        raise

    formatted_docs = cite_documents(
        runtime.context,
        graph_res.get("relevant_docs") or [],
        filenames,
    )
    if not formatted_docs:
        return "no context founded"
    return formatted_docs
