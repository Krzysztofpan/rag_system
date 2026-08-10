from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import OpenAIEmbeddings, OpenAI
from langchain_classic.retrievers import EnsembleRetriever

from langchain_core.retrievers import BaseRetriever

from app.db.session import run_async
from app.services.fts_retriever import PostgresFTSRetriever
from app.config import get_settings

settings = get_settings()

class SearchDocumentsState(TypedDict):
    query: str
    search_retry_count: int
    reranked_docs: list
    relevant_docs: list
    documents_score: int

class SearchDocumentsGraph:
    def __init__(
        self,
        fts_retriever: PostgresFTSRetriever,
        vector_store_retriever: BaseRetriever,
        llm_embedder: OpenAIEmbeddings | None = None,
        llm_evaluator: OpenAI | None = None,
    ):
        self.llm_evaluator = llm_evaluator or OpenAI(
            model=settings.evaluate_model,
            api_key=settings.openai_api_key,
        )
        self.llm_embedder = llm_embedder or OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )
        self.fts_retriever = fts_retriever
        self.vector_store_retriever = vector_store_retriever

    def build_graph(self):
        graph = StateGraph(SearchDocumentsState)

        graph.add_node("get_info", self.get_info)
        graph.add_edge("get_info", END)
        graph.set_entry_point("get_info")

        return graph.compile()

    def get_info(self, state: SearchDocumentsState):
        ensemble = EnsembleRetriever(
            retrievers=[
                self.vector_store_retriever,
                self.fts_retriever,
            ],
            weights=[
                0.7,
                0.3,
            ],
        )

        # One event loop for both async retrievers (shared SQLAlchemy pool).
        docs = run_async(ensemble.ainvoke(state["query"]))
        for doc in docs:
            print(doc.page_content)
            print("--------------------------------")
