import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_create_app_does_not_import_docling_or_ingest_parsers():
    script = """
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
    "app.services.file_ingest",
    "app.services.youtube.ingest",
]
leaked = [name for name in blocked if name in sys.modules]
assert not docling, docling
assert not leaked, leaked
"""
    env = os.environ.copy()
    env["RATE_LIMIT_STORAGE_URI"] = "memory://"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
