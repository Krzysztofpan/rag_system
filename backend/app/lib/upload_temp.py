from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import UploadFile
from starlette.datastructures import Headers

from app.config import get_settings


class UploadTooLargeError(ValueError):
    def __init__(self, *, max_bytes: int, size: int) -> None:
        self.max_bytes = max_bytes
        self.size = size
        super().__init__(f"File exceeds the {max_bytes} byte upload limit")


def _reject_if_declared_too_large(
    file: UploadFile,
    max_bytes: int | None,
) -> None:
    if max_bytes is None or file.size is None:
        return
    if file.size > max_bytes:
        raise UploadTooLargeError(max_bytes=max_bytes, size=file.size)


async def save_upload_to_temp(
    file: UploadFile,
    *,
    max_bytes: int | None,
) -> tuple[Path, int]:
    """Persist upload bytes to disk so ingest can run after the request ends.

    ``file.size`` is used only as an early reject when it is already over the
    limit. Copied bytes are always counted, so an understated size cannot
    bypass the cap.
    """
    _reject_if_declared_too_large(file, max_bytes)

    suffix = Path(file.filename or "").suffix
    size = 0
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        path = Path(tmp.name)
        try:
            while True:
                chunk = await file.read(get_settings().upload_read_chunk_bytes)
                if not chunk:
                    break
                size += len(chunk)
                if max_bytes is not None and size > max_bytes:
                    raise UploadTooLargeError(max_bytes=max_bytes, size=size)
                tmp.write(chunk)
        except Exception:
            path.unlink(missing_ok=True)
            raise
    return path, size


def upload_file_from_path(
    path: Path,
    *,
    filename: str,
    content_type: str | None,
) -> UploadFile:
    handle = path.open("rb")
    headers = Headers({"content-type": content_type} if content_type else {})
    return UploadFile(
        file=handle,
        filename=filename,
        size=path.stat().st_size,
        headers=headers,
    )
