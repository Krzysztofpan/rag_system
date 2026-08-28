from unittest.mock import AsyncMock, MagicMock, patch

from app.prompts.documents import DOCUMENTS_CATALOG_ENTRY_CHAR_LIMIT
from app.services.conversation_documents_summary import ConversationDocumentsSummarizer


def test_format_entries_clips_long_summaries():
    long_summary = "x" * (DOCUMENTS_CATALOG_ENTRY_CHAR_LIMIT + 20)
    formatted = ConversationDocumentsSummarizer().format_entries(
        [("go.md", long_summary)]
    )

    assert formatted.startswith("- go.md:\n  ")
    assert formatted.endswith("…")
    assert len(formatted) < len(long_summary) + 50


async def test_synthesize_returns_none_without_entries():
    assert await ConversationDocumentsSummarizer().synthesize([]) is None


async def test_synthesize_calls_catalog_prompt():
    chain = MagicMock()
    chain.__or__ = MagicMock(return_value=chain)
    chain.ainvoke = AsyncMock(return_value="  Catalog of two related papers.  ")

    with (
        patch(
            "app.services.conversation_documents_summary.ChatPromptTemplate.from_template",
            return_value=chain,
        ),
        patch("app.services.conversation_documents_summary.ChatOpenAI"),
    ):
        result = await ConversationDocumentsSummarizer().synthesize(
            [("a.md", "Paper A"), ("b.md", "Paper B")]
        )

    assert result == "Catalog of two related papers."
    chain.ainvoke.assert_awaited_once()
    payload = chain.ainvoke.await_args.args[0]
    assert "a.md" in payload["document_entries"]
    assert "Paper B" in payload["document_entries"]
