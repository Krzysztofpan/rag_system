import logging
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate
from app.services.fts_retriever import PostgresFTSRetriever
from app.config import get_settings
from app.lib.cohere import get_cohere_client
from app.prompts import HYDE_QUERY_REWRITE_TEMPLATE
from app.services.security import (
    PromptAttackError,
    get_prompt_shields_service,
    join_untrusted_context,
    kept_document_indexes,
    should_block_shielded_user_prompt,
    wrap_untrusted_excerpt,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class SearchDocumentsState(TypedDict):
    query: str
    user_query: str
    search_retry_count: int
    retrieved_docs: list
    relevant_docs: list
    dropped_chunk_ids: list
    doc_scores: list
    max_score: float
    rewritten_query: str
    context: str


class SearchDocumentsGraph:
    def __init__(
        self,
        fts_retriever: PostgresFTSRetriever,
        vector_store_retriever: BaseRetriever,
        llm_query_rewriter: ChatOpenAI | None = None,
    ):
        self.llm_query_rewriter = llm_query_rewriter or ChatOpenAI(model="gpt-4o-mini", temperature=0.0, max_tokens=200)
        self.fts_retriever = fts_retriever
        self.vector_store_retriever = vector_store_retriever

    def build_graph(self):
        graph = StateGraph(SearchDocumentsState)

        # nodes

        graph.add_node("get_info", self.get_info)
        graph.add_node("rerank_docs", self.rerank_docs)
        graph.add_node("query_rewrite", self.query_rewrite)
        graph.add_node("shield_docs", self.shield_docs)
        graph.add_node("build_context", self.build_context)

        # edges
        
        graph.add_edge("get_info", "rerank_docs")

        graph.add_conditional_edges("rerank_docs", self.route_after_rerank_docs, {
            "rewrite_query": "query_rewrite",
            "shield_docs": "shield_docs",
        })

        graph.add_edge("query_rewrite", "get_info")
        graph.add_edge("shield_docs", "build_context")

        graph.add_edge("build_context", END)

        graph.set_entry_point("get_info")

        return graph.compile(name="search_documents")

    async def get_info(self, state: SearchDocumentsState):
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

        query = state['rewritten_query'] if state['search_retry_count'] > 0 else state['query']

        docs = await ensemble.ainvoke(query, config={"run_name": "hybrid_retrieve"})

        return {
            "retrieved_docs": docs
        }

    async def rerank_docs(self, state: SearchDocumentsState):
        docs = state["retrieved_docs"]
        if not docs:
            return {
                "relevant_docs": [],
                "doc_scores": [],
                "max_score": 0.0,
            }

        response = await get_cohere_client().rerank(
            model=settings.cohere_rerank_model,
            query=state["query"],
            documents=[doc.page_content for doc in docs],
        )

        hits = response.results
        max_score = hits[0].relevance_score if hits else 0.0
        min_score = settings.rerank_min_score

        relevant_docs = []
        doc_scores = []
        for hit in hits:
            if hit.relevance_score < min_score:
                continue
            relevant_docs.append(docs[hit.index])
            doc_scores.append(hit.relevance_score)

        return {
            "relevant_docs": relevant_docs,
            "doc_scores": doc_scores,
            "max_score": max_score,
        }

    async def query_rewrite(self, state: SearchDocumentsState):
        # Using HYDE for rewrite query
        prompt = ChatPromptTemplate.from_template(HYDE_QUERY_REWRITE_TEMPLATE)
        chain = (prompt | self.llm_query_rewriter).with_config(
            {"run_name": "hyde_query_rewrite"}
        )

        res = await chain.ainvoke({"query": state['query']})
        
        return {
            "rewritten_query": res.content,
            "search_retry_count": state["search_retry_count"] + 1,
        }

    async def shield_docs(self, state: SearchDocumentsState):
        docs = state.get("relevant_docs") or []
        if not docs:
            return {"relevant_docs": [], "dropped_chunk_ids": []}

        user_prompt = state.get("user_query") or state.get("query") or ""
        verdict = await get_prompt_shields_service().analyze(
            user_prompt,
            [doc.page_content for doc in docs],
        )
        if should_block_shielded_user_prompt(verdict):
            raise PromptAttackError()
        kept_indexes = set(kept_document_indexes(verdict))
        dropped_chunk_ids = [
            (getattr(docs[index], "metadata", None) or {}).get("chunk_id")
            for index in range(len(docs))
            if index not in kept_indexes
        ]
        if dropped_chunk_ids:
            logger.info(
                "Prompt Shields dropped %s chunks",
                len(dropped_chunk_ids),
                extra={"dropped_chunk_ids": dropped_chunk_ids},
            )
        return {
            "relevant_docs": [docs[index] for index in range(len(docs)) if index in kept_indexes],
            "dropped_chunk_ids": dropped_chunk_ids,
        }

    def build_context(self, state: SearchDocumentsState):
        if len(state["relevant_docs"]) < 1:
            return {
                "context": "no context founded"
            }

        parts: list[str] = []
        
        for i, doc in enumerate(state["relevant_docs"], start=1):
            meta = getattr(doc, "metadata", None) or {}
            section = meta.get("context")
            pages = meta.get("pages")
            document_id = meta.get("document_id")
            chunk_id = meta.get("chunk_id")
            chunk_index = meta.get("chunk_index")

            header_bits = [f"Source {i}"]
            if document_id:
                header_bits.append(f"document_id={document_id}")
            if chunk_id:
                header_bits.append(f"chunk_id={chunk_id}")
            if chunk_index is not None:
                header_bits.append(f"chunk_index={chunk_index}")
            if pages:
                header_bits.append(f"pages={pages}")

            lines = [" | ".join(header_bits)]
            if section:
                lines.append(f"Section: {section}")
            parts.append(
                wrap_untrusted_excerpt(
                    doc.page_content,
                    header="\n".join(lines),
                )
            )

        return {
            "context": join_untrusted_context(parts)
        }

    def route_after_rerank_docs(self, state: SearchDocumentsState):
        if(len(state['relevant_docs']) == 0):
            if(state['search_retry_count'] > 0):
                return "shield_docs"

            return "rewrite_query"
        
        return "shield_docs"