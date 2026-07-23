import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from fastapi import UploadFile

from app.config import get_settings
from app.services.complex_parser import audit_markdown, convert_document


class FileTypes(str, Enum):
    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    MD = "text/markdown"
    TXT = "text/plain"


_CONTENT_TYPE_SUFFIX = {
    FileTypes.PDF: ".pdf",
    FileTypes.DOCX: ".docx",
}


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


class ParserFactory:
    def __init__(self, file: UploadFile):
        self.file = file

    def create_parser(self) -> "Parser":
        content_type = self.file.content_type or ""
        match content_type:
            case FileTypes.PDF | FileTypes.DOCX:
                return ComplexParser(self.file)
            case FileTypes.MD | FileTypes.TXT:
                return SimpleParser(self.file)
            case _:
                raise ValueError(f"Unexpected file type: {content_type!r}")


class Parser(ABC):
    def __init__(self, file: UploadFile):
        self.file = file

    @abstractmethod
    async def _parse(self) -> ParseResult:
        pass


class SimpleParser(Parser):
    async def _parse(self) -> ParseResult:
        markdown = (await self.file.read()).decode("utf-8", errors="replace")
        # Normalize accidental JSON-style escapes if a client saved escaped text.
        markdown = _ensure_real_newlines(markdown)
        report = audit_markdown(markdown)
        return ParseResult(
            markdown=markdown,
            report=report,
            filename=self.file.filename,
            content_type=self.file.content_type,
        )


class ComplexParser(Parser):
    async def _parse(self) -> ParseResult:
        settings = get_settings()
        content_type = self.file.content_type or FileTypes.PDF
        suffix = _CONTENT_TYPE_SUFFIX.get(content_type, ".pdf")
        payload = await self.file.read()

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(payload)
            tmp_path = Path(tmp.name)

        try:
            document = convert_document(
                tmp_path,
                ocr_repair=settings.parser_ocr_repair,
                llm_repair=settings.parser_llm_repair,
                llm_model=settings.parser_llm_model,
            )
            markdown = document.export_to_markdown()
        finally:
            tmp_path.unlink(missing_ok=True)

        markdown = _ensure_real_newlines(markdown)
        report = audit_markdown(markdown)
        unresolved = report.get("counts", {}).get("unresolved_glyph", 0)
        if unresolved:
            raise ParseQualityError(
                f"Document rejected: {unresolved} unresolved glyph(s) after parsing",
                report=report,
            )
        return ParseResult(
            markdown=markdown,
            report=report,
            filename=self.file.filename,
            content_type=self.file.content_type,
        )


def _ensure_real_newlines(text: str) -> str:
    """Fix text that was saved with literal \\n instead of real newlines."""
    if "\n" in text or "\\n" not in text:
        return text
    return text.replace("\\n", "\n").replace("\\t", "\t")
