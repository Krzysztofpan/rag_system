from langchain.tools import tool
from typing import Optional
from uuid import UUID

from app.services.fts_retriever import PostgresFTSRetriever
from app.graphs.search_documents_graph import SearchDocumentsGraph
from app.container import get_vector_store
from app.db.session import get_session_factory

""" 
@tool """
def search_documents(query: str, top_k: int,conversation_id: str, doc_id: Optional[str] = None) -> str:
    """
    Search info from documents in conversation context

    Args:
    query: The search query. informations that user's looking for.
    top_k: Amount of chunks relevant to retrive to answer a user question, more complicated question more amount of chunks
    doc_id: user can looking for info from only 1 document, if not specified leave empty
    """
    session_factory = get_session_factory()
    fts_retriever = PostgresFTSRetriever(
        session_factory=session_factory,
        k=top_k,
        conversation_id=UUID(conversation_id),
        document_id=UUID(doc_id) if doc_id else None,
    )
    vector_store_retriever = get_vector_store().get_retriever(
        conversation_id=conversation_id,
        k=top_k,
        session_factory=session_factory,
        document_id=UUID(doc_id) if doc_id else None,
    )
    search_documents_pipeline = SearchDocumentsGraph(fts_retriever=fts_retriever, vector_store_retriever=vector_store_retriever).build_graph()

    search_documents_pipeline.invoke({
        "query": query,
        "search_retry_count": 0,
    })

search_documents('jaki stack frontendowy jest używany?', 3, '392b5401-cf0e-4c4b-aaf1-be7cf64a8a67')
    