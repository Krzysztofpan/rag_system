from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.prompts.documents import DOCUMENTS_CATALOG_ENTRY_CHAR_LIMIT
from app.services.conversation_documents_summary import (
    ConversationDocumentsSummarizer,
    format_agent_document_catalog,
)


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


def test_format_agent_document_catalog_returns_none_without_entries():
    assert format_agent_document_catalog([], [uuid4()]) is None


def test_format_agent_document_catalog_splits_selected_and_unselected():
    dogs_id = uuid4()
    cats_id = uuid4()

    catalog = format_agent_document_catalog(
        [
            (dogs_id, "dogs.pdf", "A guide to dogs."),
            (cats_id, "cats.pdf", "A guide to cats."),
        ],
        [dogs_id],
    )

    assert catalog is not None
    selected, unselected = catalog.split("Uploaded but not selected this turn")
    assert "dogs.pdf" in selected
    assert "A guide to dogs." in selected
    assert "cats.pdf" in unselected
    assert "A guide to cats." not in catalog
    assert "<<UNTRUSTED_DOCUMENT>>" in selected
    assert "<<UNTRUSTED_DOCUMENT>>" in unselected


def test_format_agent_document_catalog_clips_selected_summaries():
    document_id = uuid4()
    long_summary = "x" * (DOCUMENTS_CATALOG_ENTRY_CHAR_LIMIT + 20)

    catalog = format_agent_document_catalog(
        [(document_id, "go.md", long_summary)],
        [document_id],
    )

    assert catalog is not None
    assert "go.md" in catalog
    assert catalog.endswith("…\n<</UNTRUSTED_DOCUMENT>>")
    assert long_summary not in catalog


def test_format_agent_document_catalog_without_selected_ids():
    catalog = format_agent_document_catalog(
        [(uuid4(), "dogs.pdf", "About dogs")],
        [],
    )

    assert catalog is not None
    assert "No documents are selected this turn" in catalog
    assert "dogs.pdf" in catalog
    assert "About dogs" not in catalog
