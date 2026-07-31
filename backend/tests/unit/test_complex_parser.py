from types import SimpleNamespace
from unittest.mock import patch

from app.services.parser.complex.parser import ComplexParser
from app.types import FileTypes
from tests.helpers import make_fake_docling_document, make_upload_file


async def test_complex_parser_uses_convert_document_and_returns_docling_doc(pdf_upload):
    fake_doc = make_fake_docling_document("# Parsed\n\nContent from PDF.")

    with patch(
        "app.services.parser.complex.parser.convert_document",
        return_value=fake_doc,
    ) as convert_mock:
        result = await ComplexParser(pdf_upload)._parse()

    convert_mock.assert_called_once()
    assert result.markdown == "# Parsed\n\nContent from PDF."
    assert result.document is fake_doc
    assert result.filename == "doc.pdf"
    assert result.content_type == FileTypes.PDF
    assert result.report["ok"] is True


async def test_complex_parser_writes_temp_file_with_docx_suffix(docx_upload):
    fake_doc = make_fake_docling_document("docx body")
    seen_paths: list[str] = []

    def _convert(path, **kwargs):  # noqa: ARG001
        seen_paths.append(str(path))
        assert str(path).endswith(".docx")
        assert path.exists()
        return fake_doc

    with patch(
        "app.services.parser.complex.parser.convert_document",
        side_effect=_convert,
    ):
        result = await ComplexParser(docx_upload)._parse()

    assert result.markdown == "docx body"
    assert seen_paths
    # temp file cleaned up after parse
    from pathlib import Path

    assert not Path(seen_paths[0]).exists()


async def test_complex_parser_audits_markdown_with_defects(pdf_upload):
    from app.services.parser.complex.ocr_repair import REPLACEMENT_CHAR

    fake_doc = SimpleNamespace(
        export_to_markdown=lambda: f"broken {REPLACEMENT_CHAR} glyph"
    )

    with patch(
        "app.services.parser.complex.parser.convert_document",
        return_value=fake_doc,
    ):
        result = await ComplexParser(pdf_upload)._parse()

    assert result.report["ok"] is False
    assert "unresolved_glyph" in result.report["counts"]
