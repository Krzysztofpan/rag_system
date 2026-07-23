from app.services.parser.base import ParseResult, Parser, ensure_real_newlines
from app.services.parser.complex.quality_audit import audit_markdown


class SimpleParser(Parser):
    async def _parse(self) -> ParseResult:
        markdown = (await self.file.read()).decode("utf-8", errors="replace")
        markdown = ensure_real_newlines(markdown)
        report = audit_markdown(markdown)
        return ParseResult(
            markdown=markdown,
            report=report,
            filename=self.file.filename,
            content_type=self.file.content_type,
        )
