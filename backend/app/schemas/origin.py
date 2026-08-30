from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class FileOrigin(BaseModel):
    kind: Literal["file"] = "file"
    file_size_bytes: int | None = None


class YoutubeOrigin(BaseModel):
    kind: Literal["youtube"] = "youtube"
    video_id: str
    url: str
    duration_sec: float | None = None
    language: str | None = None
    # "stt" = speech-to-text (Whisper fallback when captions are missing).
    transcript_source: Literal["captions", "auto_captions", "stt"] | None = None


def dump_origin(origin: FileOrigin | YoutubeOrigin) -> dict[str, Any]:
    return origin.model_dump(mode="json", exclude_none=True)
