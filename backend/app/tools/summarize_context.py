
from langchain.tools import ToolRuntime, tool
from app.services.document_service import DocumentService
from app.db.session import get_session_factory
from app.db.session import run_async
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.agent.types import AgentContext

@tool
def summarize_context(runtime: ToolRuntime[AgentContext]) -> list[dict[str, str]]:
    """
    Summarize the documents already selected for this conversation.

    Call this when the user wants a summary, overview, or recap.
    Selected document IDs are provided by the application — do not ask the user for them.
    """
    
    document_ids = runtime.context["document_ids"]
    conversation_id = runtime.context["conversation_id"]
    user_id = runtime.context["user_id"]

    async def _load():
        session_factory = get_session_factory()
        async with session_factory() as session:
            store = DocumentService(session)
            return await store.get_document_reports(
                conversation_id,
                document_ids,
                user_id=user_id,
            )

    reports = run_async(_load())

    template = """
    Summarize document based on content:

    {document_content} 
    """

    prompt = ChatPromptTemplate.from_template(template)
    
    sumarization_llm = ChatOpenAI(model="gpt-4o-mini")

    summaries = []
    
    for report in reports:
        summary_chain = prompt | sumarization_llm | StrOutputParser()

        summary = summary_chain.invoke({"document_content": report.parsed_content})
      
        summaries.append({"document_id": report.document_id, "summary": summary})

    return summaries
  