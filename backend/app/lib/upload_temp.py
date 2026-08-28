from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import UploadFile
from starlette.datastructures import Headers

_READ_CHUNK_BYTES = 64 * 1024


class UploadTooLargeError(ValueError):
    def __init__(self, *, max_bytes: int, size: int) -> None:
        self.max_bytes = max_bytes
        self.size = size
        super().__init__(f"File exceeds the {max_bytes} byte upload limit")


async def save_upload_to_temp(
    file: UploadFile,
    *,
    max_bytes: int | None,
) -> tuple[Path, int]:
    """Persist upload bytes to disk so ingest can run after the request ends."""
    if (
        max_bytes is not None
        and file.size is not None
        and file.size > max_bytes
    ):
        raise UploadTooLargeError(max_bytes=max_bytes, size=file.size)

    suffix = Path(file.filename or "").suffix
    size = 0
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        path = Path(tmp.name)
        try:
            while True:
                chunk = await file.read(_READ_CHUNK_BYTES)
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
