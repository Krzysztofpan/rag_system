from langchain.tools import ToolRuntime, tool

from app.agent.sources import cite_excerpt
from app.agent.types import AgentContext
from app.db.session import get_session_factory
from app.services.document_service import DocumentService
from app.services.security import (
    PromptAttackError,
    get_prompt_shields_service,
    join_untrusted_context,
    kept_document_indexes,
    should_block_shielded_user_prompt,
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

    summarized = [report for report in reports if report.summary]
    if not summarized:
        return ""

    summaries = [report.summary for report in summarized]
    verdict = await get_prompt_shields_service().analyze(user_query, summaries)
    if should_block_shielded_user_prompt(verdict):
        raise PromptAttackError()
    kept = [
        cite_excerpt(
            runtime.context,
            summaries[index],
            header="Summary",
            kind="summary",
            document_id=summarized[index].document_id,
        )
        for index in kept_document_indexes(verdict)
    ]
    if not kept:
        return ""
    return join_untrusted_context(kept)
