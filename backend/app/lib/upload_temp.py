from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import UploadFile
from starlette.datastructures import Headers


async def save_upload_to_temp(file: UploadFile) -> tuple[Path, int]:
    """Persist upload bytes to disk so ingest can run after the request ends."""
    suffix = Path(file.filename or "").suffix
    payload = await file.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(payload)
        path = Path(tmp.name)
    return path, len(payload)


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
