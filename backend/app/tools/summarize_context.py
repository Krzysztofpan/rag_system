
from langchain.tools import ToolRuntime, tool
from app.services.document_service import DocumentService
from app.db.session import get_session_factory
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.agent.types import AgentContext

@tool
async def summarize_context(runtime: ToolRuntime[AgentContext]) -> list[dict[str, str]]:
    """
    Summarize the documents already selected for this conversation.

    Call this when the user wants a summary, overview, or recap.
    Selected document IDs are provided by the application — do not ask the user for them.
    """
    
    document_ids = runtime.context["document_ids"]
    conversation_id = runtime.context["conversation_id"]
    user_id = runtime.context["user_id"]

    session_factory = get_session_factory()
    async with session_factory() as session:
        store = DocumentService(session)
        reports = await store.get_document_reports(
            conversation_id,
            document_ids,
            user_id=user_id,
        )


    return [report.summary for report in reports]
  