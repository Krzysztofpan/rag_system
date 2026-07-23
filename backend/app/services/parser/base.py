from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from fastapi import UploadFile


class FileTypes(str, Enum):
    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    MD = "text/markdown"
    TXT = "text/plain"


@dataclass(frozen=True)
class ParseResult:
    """Parsed document ready for preview / indexing."""

    markdown: str
    report: dict
    filename: str | None = None
    content_type: str | None = None

    @property
    def ok(self) -> bool:
        return bool(self.report.get("ok", True))


class ParseQualityError(ValueError):
    """Raised when extraction quality checks find unresolved critical defects."""

    def __init__(self, message: str, report: dict):
        super().__init__(message)
        self.report = report


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
