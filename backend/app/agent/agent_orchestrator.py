from functools import lru_cache

from langchain.agents import create_agent

from app.agent.document_grounding import DocumentGroundingMiddleware
from app.agent.types import AgentContext
from app.config import get_settings
from app.prompts import AGENT_SYSTEM_PROMPT
from app.tools import search_documents, summarize_context


def build_system_prompt() -> str:
    return AGENT_SYSTEM_PROMPT


@lru_cache(maxsize=1)
def get_agent_orchestrator():
    settings = get_settings()
    return create_agent(
        model=settings.orchestrator_model,
        tools=[search_documents, summarize_context],
        system_prompt=build_system_prompt(),
        middleware=[DocumentGroundingMiddleware()],
        context_schema=AgentContext,
    )
