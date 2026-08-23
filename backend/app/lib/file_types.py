from enum import Enum
from pathlib import Path


class FileTypes(str, Enum):
    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    MD = "text/markdown"
    TXT = "text/plain"
    PNG = "image/png"
    JPEG = "image/jpeg"
    YOUTUBE = "video/youtube"


_MIME_ALIASES = {
    "image/jpg": FileTypes.JPEG,
}

_SUFFIX_TO_TYPE = {
    ".pdf": FileTypes.PDF,
    ".docx": FileTypes.DOCX,
    ".md": FileTypes.MD,
    ".txt": FileTypes.TXT,
    ".png": FileTypes.PNG,
    ".jpg": FileTypes.JPEG,
    ".jpeg": FileTypes.JPEG,
}

DOCUMENT_FILE_TYPES = frozenset({
    FileTypes.PDF,
    FileTypes.DOCX,
    FileTypes.MD,
    FileTypes.TXT,
    FileTypes.PNG,
    FileTypes.JPEG,
})


def resolve_file_type(
    content_type: str | None,
    filename: str | None = None,
) -> FileTypes:
    """Resolve a canonical FileTypes value from MIME and/or filename suffix."""
    mime = (content_type or "").strip().lower()
    if mime in _MIME_ALIASES:
        return _MIME_ALIASES[mime]
    for member in FileTypes:
        if member.value == mime:
            return member
    suffix = Path(filename or "").suffix.lower()
    if suffix in _SUFFIX_TO_TYPE:
        return _SUFFIX_TO_TYPE[suffix]
    raise ValueError(f"Unexpected file type: {content_type!r}")


def resolve_document_file_type(
    content_type: str | None,
    filename: str | None = None,
) -> FileTypes:
    """Resolve a file type that this endpoint can ingest as an uploaded document."""
    resolved = resolve_file_type(content_type, filename)
    if resolved not in DOCUMENT_FILE_TYPES:
        raise ValueError(f"Unexpected file type: {content_type!r}")
    return resolved
