from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import UploadFile

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument


@dataclass(frozen=True)
class ParseResult:
    """Parsed document ready for preview / indexing."""

    markdown: str
    report: dict
    filename: str | None = None
    content_type: str | None = None
    document: "DoclingDocument | None" = None

    @property
    def ok(self) -> bool:
        return bool(self.report.get("ok", True))


class ParseQualityError(ValueError):
    """Raised when too many chunks fail critical extraction quality checks."""

    def __init__(
        self,
        message: str,
        report: dict,
        document_id: UUID | None = None,
        parsed_content: str | None = None,
    ):
        super().__init__(message)
        self.report = report
        self.document_id = document_id
        self.parsed_content = parsed_content


class Parser(ABC):
    def __init__(self, file: UploadFile):
        self.file = file

    @abstractmethod
    async def _parse(self) -> ParseResult:
        pass


def ensure_real_newlines(text: str) -> str:
    """Fix text that was saved with literal \\n instead of real newlines."""
    if "\n" in text or "\\n" not in text:
        return text
    return text.replace("\\n", "\n").replace("\\t", "\t")
