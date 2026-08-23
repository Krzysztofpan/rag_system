from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, TypeAdapter


class FileOrigin(BaseModel):
    kind: Literal["file"] = "file"
    file_size_bytes: int | None = None


class YoutubeOrigin(BaseModel):
    kind: Literal["youtube"] = "youtube"
    video_id: str
    url: str
    duration_sec: float | None = None
    language: str | None = None
    transcript_source: Literal["captions", "auto_captions", "stt"] | None = None


DocumentOrigin = Annotated[
    FileOrigin | YoutubeOrigin,
    Field(discriminator="kind"),
]

_origin_adapter = TypeAdapter(DocumentOrigin)


def dump_origin(origin: FileOrigin | YoutubeOrigin) -> dict[str, Any]:
    return origin.model_dump(mode="json", exclude_none=True)


def parse_origin(data: dict[str, Any] | None) -> FileOrigin | YoutubeOrigin | None:
    if data is None:
        return None
    return _origin_adapter.validate_python(data)
