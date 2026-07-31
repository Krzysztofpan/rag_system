from app.services.parser.base import ensure_real_newlines
from app.services.parser.simple import SimpleParser
from app.types import FileTypes
from tests.helpers import make_upload_file


def test_ensure_real_newlines_converts_literal_escapes():
    assert ensure_real_newlines("line1\\nline2\\tindented") == "line1\nline2\tindented"


def test_ensure_real_newlines_leaves_real_newlines_alone():
    text = "line1\nline2"
    assert ensure_real_newlines(text) is text


async def test_simple_parser_reads_markdown_and_audits():
    upload = make_upload_file(
        "# Hello\n\nWorld",
        content_type=FileTypes.MD,
        filename="hello.md",
    )
    result = await SimpleParser(upload)._parse()

    assert result.markdown == "# Hello\n\nWorld"
    assert result.filename == "hello.md"
    assert result.content_type == FileTypes.MD
    assert result.document is None
    assert result.report["ok"] is True
    assert result.ok is True


async def test_simple_parser_fixes_literal_newlines():
    upload = make_upload_file(
        "# Title\\n\\nBody",
        content_type=FileTypes.TXT,
        filename="note.txt",
    )
    result = await SimpleParser(upload)._parse()
    assert result.markdown == "# Title\n\nBody"


async def test_simple_parser_replaces_invalid_utf8():
    upload = make_upload_file(
        b"ok \xff text",
        content_type=FileTypes.TXT,
        filename="bin.txt",
    )
    result = await SimpleParser(upload)._parse()
    assert "ok " in result.markdown
    assert "text" in result.markdown
