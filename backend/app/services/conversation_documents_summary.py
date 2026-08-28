from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.prompts import (
    DOCUMENTS_CATALOG_ENTRY_CHAR_LIMIT,
    DOCUMENTS_CATALOG_TEMPLATE,
)


class ConversationDocumentsSummarizer:
    def format_entries(self, entries: list[tuple[str, str]]) -> str:
        blocks = []
        for filename, summary in entries:
            clipped = summary.strip()
            if len(clipped) > DOCUMENTS_CATALOG_ENTRY_CHAR_LIMIT:
                clipped = clipped[:DOCUMENTS_CATALOG_ENTRY_CHAR_LIMIT].rstrip() + "…"
            blocks.append(f"- {filename}:\n  {clipped}")
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
