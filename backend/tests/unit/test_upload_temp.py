from pathlib import Path

import pytest

from app.lib.file_types import FileTypes
from app.lib.upload_temp import (
    UploadTooLargeError,
    save_upload_to_temp,
    upload_file_from_path,
)
from tests.helpers import make_upload_file


async def test_save_upload_to_temp_and_reopen_roundtrip():
    upload = make_upload_file("# hi", content_type=FileTypes.MD, filename="note.md")
    path, size = await save_upload_to_temp(upload, max_bytes=1024)
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


async def test_save_upload_to_temp_rejects_oversize_before_writing():
    upload = make_upload_file("too big", content_type=FileTypes.MD, filename="note.md")
    with pytest.raises(UploadTooLargeError) as exc_info:
        await save_upload_to_temp(upload, max_bytes=3)
    assert exc_info.value.max_bytes == 3
    assert exc_info.value.size == upload.size


async def test_save_upload_to_temp_rejects_oversize_while_streaming():
    upload = make_upload_file("hello world", content_type=FileTypes.MD, filename="note.md")
    upload.size = None
    with pytest.raises(UploadTooLargeError) as exc_info:
        await save_upload_to_temp(upload, max_bytes=5)
    assert exc_info.value.size > 5


async def test_save_upload_to_temp_skips_size_check_when_unlimited():
    upload = make_upload_file("hello world", content_type=FileTypes.MD, filename="note.md")
    path, size = await save_upload_to_temp(upload, max_bytes=None)
    try:
        assert size == upload.size
    finally:
        path.unlink(missing_ok=True)
