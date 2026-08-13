from functools import lru_cache

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt

from app.agent.types import AgentContext
from app.config import get_settings
from app.tools import search_documents, summarize_context


def build_system_prompt(document_count: int) -> str:
    if document_count:
        selection = (
            f"The user has already selected {document_count} document(s) for this request. "
            "Those documents are injected into tools automatically. "
            "Never ask for document IDs, conversation ID, user ID, or permission to use tools."
        )
    else:
        selection = (
            "No documents are currently selected. "
            "If the user asks about document content, tell them to select documents first."
        )

    return (
        "You are an assistant that helps the user work with documents in the current conversation.\n"
        f"{selection}\n"
        "If the user wants a summary, overview, or recap, call summarize_context immediately.\n"
        "If the user asks a specific question about the documents, call search_documents.\n"
        "Answer based on tool results. If the tools return no information, say you could not find it in the documents."
    )


def agent_system_prompt(request: ModelRequest) -> str:
    context = request.runtime.context or {}
    document_ids = context.get("document_ids") or []
    return build_system_prompt(len(document_ids))


@lru_cache(maxsize=1)
def get_agent_orchestrator():
    return create_agent(
        model=get_settings().orchestrator_model,
        tools=[search_documents, summarize_context],
        middleware=[dynamic_prompt(agent_system_prompt)],
        context_schema=AgentContext,
    )
