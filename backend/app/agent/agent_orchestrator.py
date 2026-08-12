from typing import TypedDict
from uuid import UUID

from langchain.agents import create_agent

from app.tools import search_documents, summarize_context
from app.agent.types import AgentContext

from app.config import get_settings
settings = get_settings()


agent_orchestrator = create_agent(
    model=settings.orchestrator_model,
    tools=[search_documents, summarize_context],
    system_prompt="You are assistant who's helps user working with documents, "
    "you have to answer a user question in nice way, don't ask user for permisions to run tool's,"
    "if you don't know something ask user for more informations if it's helpfull if not just say i don't know or i don't find this information in document",
    context_schema=AgentContext,
)
