from functools import lru_cache

from langchain.agents import create_agent

from app.agent.types import AgentContext
from app.config import get_settings
from app.tools import search_documents, summarize_context


def build_system_prompt() -> str:
    return (
        "You are an assistant that helps the user work with documents in the current conversation.\n"
        "Documents selected for the current request are injected into tools automatically. "
        "Never ask for document IDs, conversation ID, user ID, or permission to use tools.\n"
        "If the user wants a summary, overview, or recap, call summarize_context immediately.\n"
        "If the user asks a specific question about the documents, call search_documents.\n"
        "Answer document questions from current tool results, not from conversation memory. "
        "If tools return no information, tell the user that no information was found and "
        "that they may need to select documents."
    )


@lru_cache(maxsize=1)
def get_agent_orchestrator():
    settings = get_settings()
    return create_agent(
        model=settings.orchestrator_model,
        tools=[search_documents, summarize_context],
        system_prompt=build_system_prompt(),
        context_schema=AgentContext,
    )
