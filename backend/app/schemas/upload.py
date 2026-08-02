from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ParseIssue(BaseModel):
    line: int
    kinds: list[str]
    text: str


class ParseReport(BaseModel):
    ok: bool
    counts: dict[str, int] = Field(default_factory=dict)
    issues: list[ParseIssue] = Field(default_factory=list)


class RejectedChunk(BaseModel):
    index: int
    kinds: list[str]
    text: str


class ChunkQuality(BaseModel):
    ok: bool
    total_chunks: int
    kept_chunks: int
    rejected_chunks: int
    rejected_ratio: float
    max_rejected_ratio: float
    rejected: list[RejectedChunk] = Field(default_factory=list)


class UploadQuality(BaseModel):
    parse_report: ParseReport
    chunk_quality: ChunkQuality


class UploadResourceResponse(BaseModel):
    status: Literal["ready", "rejected"]
    document_id: str | None = None
    parsed_content: str | None = None
    quality: UploadQuality | None = None
    error: str | None = None


def _public_chunk_quality(chunk_quality: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in chunk_quality.items() if key != "kept_indexes"}


def build_upload_quality(
    *,
    parse_report: dict[str, Any],
    chunk_quality: dict[str, Any],
) -> UploadQuality:
    return UploadQuality(
        parse_report=ParseReport.model_validate(parse_report),
        chunk_quality=ChunkQuality.model_validate(_public_chunk_quality(chunk_quality)),
    )


def quality_from_rejected_report(report: dict[str, Any]) -> UploadQuality | None:
    chunk_quality = report.get("chunk_quality")
    if not isinstance(chunk_quality, dict):
        return None

    parse_report = {key: value for key, value in report.items() if key != "chunk_quality"}
    return build_upload_quality(parse_report=parse_report, chunk_quality=chunk_quality)
