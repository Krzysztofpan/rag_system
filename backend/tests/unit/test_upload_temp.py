from pathlib import Path

from app.lib.file_types import FileTypes
from app.lib.upload_temp import save_upload_to_temp, upload_file_from_path
from tests.helpers import make_upload_file


async def test_save_upload_to_temp_and_reopen_roundtrip():
    upload = make_upload_file("# hi", content_type=FileTypes.MD, filename="note.md")
    path, size = await save_upload_to_temp(upload)
    try:
        assert size == upload.size
        assert path.exists()
        assert path.suffix == ".md"
        reopened = upload_file_from_path(
            path,
            filename="note.md",
            content_type=FileTypes.MD,
        )
        try:
            assert await reopened.read() == b"# hi"
            assert reopened.filename == "note.md"
            assert reopened.content_type == FileTypes.MD
        finally:
            await reopened.close()
    finally:
        path.unlink(missing_ok=True)
        assert isinstance(path, Path)
        assert not path.exists()
