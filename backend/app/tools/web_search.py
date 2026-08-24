from langchain.tools import ToolRuntime, tool
from langchain_tavily import TavilySearch

from app.agent.types import AgentContext
from app.config import get_settings
from app.services.security import (
    PromptAttackError,
    get_prompt_shields_service,
    join_untrusted_context,
    kept_document_indexes,
    should_block_shielded_user_prompt,
    wrap_untrusted_excerpt,
)


def build_tavily_search() -> TavilySearch:
    api_key = get_settings().tavily_api_key
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY is not configured")
    return TavilySearch(tavily_api_key=api_key)


@tool
async def web_search_tavily(query: str, runtime: ToolRuntime[AgentContext]) -> str:
    """
    Search the public web for current or external information.

    Call this when the question cannot be answered from the selected documents:
    recent events, public facts, or information the user explicitly wants from
    the internet. Do not use this instead of search_documents when the question
    is about the conversation's files.

    The search query is provided by the application — do not ask the user for it.

    Return Value:
    Web page excerpts with URL and title metadata.
    """
    user_query = runtime.context.get("user_query") or ""

    response = await build_tavily_search().ainvoke({"query": query})
    results = response.get("results") if isinstance(response, dict) else None
    pages = [
        page
        for page in results or []
        if isinstance(page, dict) and page.get("content")
    ]
    pages_content = [page["content"] for page in pages]
    if not pages_content:
        return ""

    verdict = await get_prompt_shields_service().analyze(user_query, pages_content)
    if should_block_shielded_user_prompt(verdict):
        raise PromptAttackError()
    kept = [
        wrap_untrusted_excerpt(
            pages_content[index],
            header=f"URL: {pages[index].get('url', '')}, Title: {pages[index].get('title', '')}",
        )
        for index in kept_document_indexes(verdict)
    ]
    if not kept:
        return ""
    return join_untrusted_context(kept)
