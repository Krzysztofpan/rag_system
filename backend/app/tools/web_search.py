from langchain.tools import ToolRuntime, tool

from app.agent.sources import cite_excerpt
from app.agent.types import AgentContext
from app.lib.tavily import get_tavily_client
from app.services.security import (
    PromptAttackError,
    get_prompt_shields_service,
    join_untrusted_context,
    kept_document_indexes,
    should_block_shielded_user_prompt,
    wrap_untrusted_excerpt,
)


@tool
async def web_search(query: str, top_k: int, runtime: ToolRuntime[AgentContext]) -> str:
    """
    Search the public web for current or external information.

    Call this when the question cannot be answered from the selected documents:
    recent events, public facts, or information the user explicitly wants from
    the internet. Do not use this instead of search_documents when the question
    is about the conversation's files.

    Args:
    query: The search query. informations that user's looking for.
    top_k: Amount of articles to retrive from web.

    Return Value:
    Numbered web excerpts labeled [n], with URL and title metadata.
    """
    user_query = runtime.context.get("user_query") or ""
    client = get_tavily_client()
    response = await client.search(query=query, max_results=top_k)
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
    kept = []
    for index in kept_document_indexes(verdict):
        page = pages[index]
        url = page.get("url") or ""
        title = page.get("title") or ""
        header = f"URL: {url}, Title: {title}"
        if url:
            kept.append(
                cite_excerpt(
                    runtime.context,
                    pages_content[index],
                    header=header,
                    kind="web",
                    url=url,
                )
            )
            continue
        kept.append(wrap_untrusted_excerpt(pages_content[index], header=header))
    if not kept:
        return ""
    return join_untrusted_context(kept)
