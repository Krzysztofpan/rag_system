from collections.abc import Sequence
from uuid import UUID

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.prompts import (
    DOCUMENTS_CATALOG_ENTRY_CHAR_LIMIT,
    DOCUMENTS_CATALOG_TEMPLATE,
)
from app.services.security import wrap_untrusted_excerpt


def clip_catalog_summary(summary: str) -> str:
    clipped = summary.strip()
    if len(clipped) > DOCUMENTS_CATALOG_ENTRY_CHAR_LIMIT:
        return clipped[:DOCUMENTS_CATALOG_ENTRY_CHAR_LIMIT].rstrip() + "…"
    return clipped


def format_agent_document_catalog(
    entries: Sequence[tuple[UUID, str, str | None]],
    selected_ids: Sequence[UUID],
) -> str | None:
    if not entries:
        return None

    selected_set = set(selected_ids)
    selected = [entry for entry in entries if entry[0] in selected_set]
    unselected = [entry for entry in entries if entry[0] not in selected_set]
    parts: list[str] = []

    if selected:
        blocks = []
        for _, filename, summary in selected:
            if summary and summary.strip():
                blocks.append(f"- {filename}:\n  {clip_catalog_summary(summary)}")
            else:
                blocks.append(f"- {filename}")
        parts.append(
            wrap_untrusted_excerpt(
                "\n\n".join(blocks),
                header="Selected this turn (searchable with search_documents)",
            )
        )
    else:
        parts.append(
            "No documents are selected this turn. "
            "search_documents has no files to search."
        )

    if unselected:
        names = "\n".join(filename for _, filename, _ in unselected)
        parts.append(
            wrap_untrusted_excerpt(
                names,
                header="Uploaded but not selected this turn",
            )
        )

    return "\n\n".join(parts)


class ConversationDocumentsSummarizer:
    def format_entries(self, entries: list[tuple[str, str]]) -> str:
        blocks = []
        for filename, summary in entries:
            blocks.append(f"- {filename}:\n  {clip_catalog_summary(summary)}")
        return "\n\n".join(blocks)

    async def synthesize(self, entries: list[tuple[str, str]]) -> str | None:
        if not entries:
            return None

        prompt = ChatPromptTemplate.from_template(DOCUMENTS_CATALOG_TEMPLATE)
        catalog_llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=400)
        catalog_chain = prompt | catalog_llm | StrOutputParser()
        summary = await catalog_chain.ainvoke(
            {"document_entries": self.format_entries(entries)},
            config={"run_name": "synthesize_documents_summary"},
        )
        catalog = summary.strip()
        return catalog or None
