from __future__ import annotations

from typing import Literal

from app.db.models.document import Document
from app.db.models.document_report import DocumentReport
from app.schemas.base import APIModel
from app.schemas.upload import UploadQuality


class ResourceResponse(APIModel):
    id: str
    filename: str
    content_type: str | None
    status: Literal["pending", "processing", "ready", "failed"]
    error: str | None = None
    chunk_count: int = 0


class ResourceReportResponse(APIModel):
    document_id: str
    parsed_content: str | None = None
    quality: UploadQuality | None = None


class GetResourcesResponse(APIModel):
    count: int
    conversation_resources: list[ResourceResponse]


class UploadResourceResponse(APIModel):
    resource: ResourceResponse | None = None
    report: ResourceReportResponse | None = None
    error: str | None = None


def resource_from_document(document: Document) -> ResourceResponse:
    return ResourceResponse(
        id=str(document.id),
        filename=document.filename,
        content_type=document.content_type,
        status=document.status.value,
        error=document.error_message,
        chunk_count=document.chunk_count,
    )


def report_from_document_report(report: DocumentReport) -> ResourceReportResponse:
    quality = None
    if report.quality is not None:
        quality = UploadQuality.model_validate(report.quality)

    return ResourceReportResponse(
        document_id=str(report.document_id),
        parsed_content=report.parsed_content,
        quality=quality,
    )
