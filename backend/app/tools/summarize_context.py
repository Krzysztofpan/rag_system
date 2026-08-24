
from langchain.tools import ToolRuntime, tool
from app.services.document_service import DocumentService
from app.db.session import get_session_factory
from app.agent.types import AgentContext
from app.services.security import (
    PromptAttackError,
    get_prompt_shields_service,
    join_untrusted_context,
    kept_document_indexes,
    should_block_shielded_user_prompt,
    wrap_untrusted_excerpt,
)


@tool
async def summarize_context(runtime: ToolRuntime[AgentContext]) -> str:
    """
    Summarize the documents already selected for this conversation.

    Call this when the user wants a summary, overview, or recap.
    Selected document IDs are provided by the application — do not ask the user for them.
    """
    
    document_ids = runtime.context["document_ids"]
    conversation_id = runtime.context["conversation_id"]
    user_id = runtime.context["user_id"]
    user_query = runtime.context.get("user_query") or ""

    session_factory = get_session_factory()
    async with session_factory() as session:
        store = DocumentService(session)
        reports = await store.get_document_reports(
            conversation_id,
            document_ids,
            user_id=user_id,
        )

    summaries = [report.summary for report in reports if report.summary]
    if not summaries:
        return ""

    verdict = await get_prompt_shields_service().analyze(user_query, summaries)
    if should_block_shielded_user_prompt(verdict):
        raise PromptAttackError()
    kept = [
        wrap_untrusted_excerpt(summaries[index], header=f"Summary {i}")
        for i, index in enumerate(kept_document_indexes(verdict), start=1)
    ]
    if not kept:
        return ""
    return join_untrusted_context(kept)
