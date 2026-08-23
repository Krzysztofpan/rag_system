from __future__ import annotations

from typing import Literal

from app.db.models.document import Document
from app.db.models.document_report import DocumentReport
from app.schemas.base import APIModel
from app.schemas.upload import UploadQuality


class SourceResponse(APIModel):
    id: str
    filename: str
    content_type: str | None
    status: Literal["pending", "processing", "ready", "failed"]
    error: str | None = None


class SourceReportResponse(APIModel):
    document_id: str
    parsed_content: str | None = None
    summary: str | None = None
    quality: UploadQuality | None = None


class GetSourcesResponse(APIModel):
    count: int
    conversation_sources: list[SourceResponse]


class DeleteSourceResponse(APIModel):
    deleted_document: Document


class IngestUrlRequest(APIModel):
    url: str


def source_from_document(document: Document) -> SourceResponse:
    return SourceResponse(
        id=str(document.id),
        filename=document.filename,
        content_type=document.content_type,
        status=document.status.value,
        error=document.error_message,
    )


def report_from_document_report(report: DocumentReport) -> SourceReportResponse:
    quality = None
    if report.quality is not None:
        quality = UploadQuality.model_validate(report.quality)

    return SourceReportResponse(
        document_id=str(report.document_id),
        parsed_content=report.parsed_content,
        summary=report.summary,
        quality=quality,
    )
