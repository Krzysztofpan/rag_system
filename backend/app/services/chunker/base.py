from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

import tiktoken

from app.config import get_settings

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument


@dataclass(frozen=True)
class ChunkResult:
    """Normalized chunk for both HybridChunker and text-splitter paths.

    content: clean chunk body (quotes, BM25, char offsets).
    context: optional structural prefix (headings / section path); never folded into content.
    pages: PDF page numbers touched by the chunk (Complex only).
    char_start / char_end: [start, end) in ParseResult.markdown when mapping is exact.
    token_count: token length of content (embedding-model tokenizer).
    """

    content: str
    context: str | None = None
    pages: list[int] | None = None
    char_start: int | None = None
    char_end: int | None = None
    token_count: int | None = None


class Chunker(ABC):
    def __init__(self, content_type):
        settings = get_settings()
        self.content_type = content_type
        self.tokenizer = tiktoken.encoding_for_model(settings.embedding_model)
        self.embedding_model_max_tokens = settings.embedding_model_max_tokens
        self.text_splitter = None

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    @abstractmethod
    def _chunk(
        self, *, doc: "str | DoclingDocument", source_text: str
    ) -> list[ChunkResult]:
        pass
