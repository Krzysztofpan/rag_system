import tempfile
from pathlib import Path

from app.config import get_settings
from app.services.parser.base import (
    FileTypes,
    ParseQualityError,
    ParseResult,
    Parser,
    ensure_real_newlines,
)
from app.services.parser.complex.converter import convert_document
from app.services.parser.complex.quality_audit import audit_markdown

_CONTENT_TYPE_SUFFIX = {
    FileTypes.PDF: ".pdf",
    FileTypes.DOCX: ".docx",
}


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

        markdown = ensure_real_newlines(markdown)
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
