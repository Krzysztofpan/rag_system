from typing import TYPE_CHECKING

from docling.chunking import HybridChunker
from docling_core.transforms.chunker.base import BaseChunk
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer

from app.services.chunker.base import ChunkResult, Chunker

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument


class ComplexChunker(Chunker):
    def __init__(self, content_type):
        super().__init__(content_type)

        self.text_splitter = HybridChunker(
            tokenizer=OpenAITokenizer(
                tokenizer=self.tokenizer,
                max_tokens=self.embedding_model_max_tokens,
            ),
            merge_peers=True,
        )

    def generate_context(self, chunk: BaseChunk) -> str | None:
        """Structural prefix from HybridChunker.contextualize, without the chunk body."""
        serialized = self.text_splitter.contextualize(chunk)
        body = chunk.text
        if not serialized.endswith(body):
            return serialized or None

        prefix = serialized[: -len(body)] if body else serialized
        delim = self.text_splitter.delim
        if delim and prefix.endswith(delim):
            prefix = prefix[: -len(delim)]
        prefix = prefix.strip()
        return prefix or None

    def get_pages(self, chunk: BaseChunk) -> list[int] | None:
        """Unique page numbers touched by the chunk, in document order."""
        pages: list[int] = []
        seen: set[int] = set()
        doc_items = getattr(chunk.meta, "doc_items", None) or []
        for item in doc_items:
            for prov in getattr(item, "prov", None) or []:
                page_no = getattr(prov, "page_no", None)
                if page_no is None:
                    continue
                page = int(page_no)
                if page not in seen:
                    seen.add(page)
                    pages.append(page)
        return pages or None

    def resolve_offsets(
        self, content: str, markdown: str, search_from: int
    ) -> tuple[int | None, int | None, int]:
        """Exact substring match in markdown; NULL offsets when not found.

        Returns (char_start, char_end, next_search_from).
        """
        if not content:
            return None, None, search_from

        char_start = markdown.find(content, search_from)
        if char_start < 0:
            return None, None, search_from

        char_end = char_start + len(content)
        return char_start, char_end, char_start + 1

    def _chunk(
        self, *, doc: "DoclingDocument", source_text: str
    ) -> list[ChunkResult]:
        results: list[ChunkResult] = []
        search_from = 0
        for chunk in self.text_splitter.chunk(dl_doc=doc):
            content = chunk.text
            char_start, char_end, search_from = self.resolve_offsets(
                content, source_text, search_from
            )
            results.append(
                ChunkResult(
                    content=content,
                    context=self.generate_context(chunk),
                    pages=self.get_pages(chunk),
                    char_start=char_start,
                    char_end=char_end,
                    token_count=self.count_tokens(content),
                )
            )
        return results
