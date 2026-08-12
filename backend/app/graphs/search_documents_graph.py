from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_classic.retrievers import EnsembleRetriever
from pydantic import Field, BaseModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate
from app.db.session import run_async
from app.services.fts_retriever import PostgresFTSRetriever
from app.config import get_settings

settings = get_settings()

class EvaluatorResponse(BaseModel):
    evaluate_result: bool = Field(description="evaluate result from comparing doc to question")

class SearchDocumentsState(TypedDict):
    query: str
    search_retry_count: int
    reranked_docs: list
    relevant_docs: list
    documents_score: int
    rewritten_query: str
    context: str


class SearchDocumentsGraph:
    def __init__(
        self,
        fts_retriever: PostgresFTSRetriever,
        vector_store_retriever: BaseRetriever,
        llm_embedder: OpenAIEmbeddings | None = None,
        llm_evaluator: ChatOpenAI | None = None,
        llm_query_rewriter: ChatOpenAI | None = None,
    ):
        self.llm_evaluator = llm_evaluator or ChatOpenAI(
            model=settings.evaluate_model,
        )
        self.llm_embedder = llm_embedder or OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )
        self.llm_query_rewriter = llm_query_rewriter or ChatOpenAI(model="gpt-4o-mini", temperature=0.0, max_tokens=200)
        self.fts_retriever = fts_retriever
        self.vector_store_retriever = vector_store_retriever

    def build_graph(self):
        graph = StateGraph(SearchDocumentsState)

        # nodes

        graph.add_node("get_info", self.get_info)
        graph.add_node("evaluate_docs", self.evaluate_docs)
        graph.add_node("query_rewrite", self.query_rewrite)
        graph.add_node("build_context", self.build_context)

        # edges
        
        graph.add_edge("get_info", "evaluate_docs")

        graph.add_conditional_edges("evaluate_docs", self.route_after_evaluate_docs, {
            "rewrite_query": "query_rewrite",
            "build_context": "build_context",
        })

        graph.add_edge("query_rewrite", "get_info")

        graph.add_edge("build_context", END)

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

        query = state['rewritten_query'] if state['search_retry_count'] > 0 else state['query']
        
        docs = run_async(ensemble.ainvoke(query))
        
        return {
            "reranked_docs": docs
        }

    def evaluate_docs(self, state: SearchDocumentsState):

        relevant_docs = []

        for doc in state['reranked_docs']:
            template = """
            evaluate that document is relevant to answer the question:
            {doc}

            question: {question}
            """

            prompt = ChatPromptTemplate.from_template(template)
            structured_evaluator = self.llm_evaluator.with_structured_output(EvaluatorResponse) 
            chain = prompt | structured_evaluator
            res = chain.invoke({"doc": doc, "question": state['query']})

            if(res.evaluate_result):
                relevant_docs.append(doc)
            else:
                continue

        return {
            "relevant_docs": relevant_docs
        }

    def query_rewrite(self, state: SearchDocumentsState):
        # Using HYDE for rewrite query
        template = """
        Please write a scientific paper passage to answer the question.

        question: {query}
        """

        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm_query_rewriter

        res = chain.invoke({"query": state['query']})
        
        return {
            "rewritten_query": res.content,
            "search_retry_count": state["search_retry_count"] + 1,
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
            lines.append(doc.page_content.strip())
            parts.append("\n".join(lines))

        return {
            "context": "\n\n---\n\n".join(parts)
        }

    def route_after_evaluate_docs(self, state: SearchDocumentsState):
        if(len(state['relevant_docs']) == 0):
            if(state['search_retry_count'] > 0):
                return "build_context"

            return "rewrite_query"
        
        return "build_context"