import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]

_HEAVY_MODULES = """
heavy = [
    name
    for name in sys.modules
    if name == "docling"
    or name.startswith("docling.")
    or name == "rapidocr"
    or name.startswith("rapidocr.")
]
blocked = [
    "app.services.parser.complex.parser",
    "app.services.parser.complex.converter",
    "app.services.parser.complex.ocr_repair",
    "app.services.chunker.complex",
]
leaked = [name for name in blocked if name in sys.modules]
assert not heavy, heavy
assert not leaked, leaked
"""


def _run_isolation_script(script: str, extra_env: dict[str, str] | None = None) -> None:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_create_app_does_not_import_docling_or_ingest_parsers():
    _run_isolation_script(
        """
import sys
from app.app import create_app

create_app()
docling = [
    name
    for name in sys.modules
    if name == "docling" or name.startswith("docling.")
]
blocked = [
    "app.services.parser.factory",
    "app.services.parser.complex.converter",
    "app.services.parser.complex.parser",
    "app.ingest.factory",
    "app.ingest.summary",
    "app.services.document.file_ingest",
    "app.services.youtube.ingest",
]
leaked = [name for name in blocked if name in sys.modules]
assert not docling, docling
assert not leaked, leaked
""",
        extra_env={"RATE_LIMIT_STORAGE_URI": "memory://"},
    )


def test_markdown_ingest_path_does_not_import_docling_or_rapidocr():
    _run_isolation_script(
        f"""
import sys
from io import BytesIO

from fastapi import UploadFile
from starlette.datastructures import Headers

from app.lib.file_types import FileTypes
from app.services.chunker.factory import ChunkerFactory
from app.services.chunker.simple import SimpleChunker
from app.services.document.file_ingest import FileIngestService
from app.services.parser.factory import ParserFactory
from app.services.parser.simple import SimpleParser

upload = UploadFile(
    file=BytesIO(b"# hi\\n"),
    filename="note.md",
    size=5,
    headers=Headers({{"content-type": FileTypes.MD}}),
)
parser = ParserFactory.create_parser(upload)
assert isinstance(parser, SimpleParser)
chunker = ChunkerFactory.create_chunker(FileTypes.MD)
assert isinstance(chunker, SimpleChunker)
FileIngestService
{_HEAVY_MODULES}
"""
    )


def test_quality_audit_does_not_import_ocr_repair():
    _run_isolation_script(
        f"""
import sys
from app.services.parser.complex.quality_audit import audit_markdown

assert audit_markdown("# ok")["ok"] is True
assert "app.services.parser.complex.ocr_repair" not in sys.modules
{_HEAVY_MODULES}
"""
    )
