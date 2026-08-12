from langchain.agents import create_agent
from app.config import get_settings
from app.agent.tools import search_documents

settings = get_settings()

agent_orchestrator = create_agent(
    model=settings.orchestrator_model, 
    tools=[search_documents]
)
