from pathlib import Path
from types import SimpleNamespace

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


async def test_save_upload_to_temp_rejects_declared_size_without_reading():
    upload = make_upload_file("too big", content_type=FileTypes.MD, filename="note.md")

    async def fail_read(*_args, **_kwargs):
        raise AssertionError("declared oversize uploads must not be read")

    upload.read = fail_read  # type: ignore[method-assign]
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


async def test_save_upload_to_temp_rejects_when_declared_size_understates_body():
    upload = make_upload_file("hello world", content_type=FileTypes.MD, filename="note.md")
    upload.size = 3
    with pytest.raises(UploadTooLargeError) as exc_info:
        await save_upload_to_temp(upload, max_bytes=5)
    assert exc_info.value.size > 5


async def test_save_upload_to_temp_uses_configured_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.lib.upload_temp.get_settings",
        lambda: SimpleNamespace(
            upload_temp_dir=tmp_path,
            upload_read_chunk_bytes=64 * 1024,
        ),
    )
    upload = make_upload_file("# hi", content_type=FileTypes.MD, filename="note.md")
    path, _size = await save_upload_to_temp(upload, max_bytes=1024)
    try:
        assert path.parent == tmp_path
    finally:
        path.unlink(missing_ok=True)


async def test_save_upload_to_temp_skips_size_check_when_unlimited():
    upload = make_upload_file("hello world", content_type=FileTypes.MD, filename="note.md")
    path, size = await save_upload_to_temp(upload, max_bytes=None)
    try:
        assert size == upload.size
    finally:
        path.unlink(missing_ok=True)
