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

def get_structured_llm(structure: BaseModel, model="gpt-4o-mini"):
    return ChatOpenAI(model=model).with_structured_output(structure)


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
        llm_evaluator: ChatOpenAI | None = None,
    ):
        self.llm_evaluator = llm_evaluator or ChatOpenAI(
            model=settings.evaluate_model,
        )
        self.llm_embedder = llm_embedder or OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )
        self.fts_retriever = fts_retriever
        self.vector_store_retriever = vector_store_retriever

    def build_graph(self):
        graph = StateGraph(SearchDocumentsState)

        # nodes
        graph.add_node("get_info", self.get_info)
        graph.add_node("evaluate_docs", self.evaluate_docs)

        # edges
        graph.add_edge("get_info", "evaluate_docs")
        graph.add_edge("evaluate_docs", END)

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

        docs = run_async(ensemble.ainvoke(state["query"]))
        
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
            llm = get_structured_llm(EvaluatorResponse)
            chain = prompt | llm
            res = chain.invoke({"doc": doc, "question": state['query']})

            if(res.evaluate_result):
                relevant_docs.append(doc)
            else:
                continue

        return {
            "relevant_docs": relevant_docs
        }