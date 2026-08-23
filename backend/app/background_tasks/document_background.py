from uuid import UUID

from app.services.file_ingest import FileIngestService


async def ingest_document_source(
    conversation_id: UUID,
    document_id: UUID,
    user_id: UUID,
    path: str,
    filename: str,
    content_type: str | None,
) -> None:
    await FileIngestService().ingest(
        conversation_id=conversation_id,
        document_id=document_id,
        user_id=user_id,
        path=path,
        filename=filename,
        content_type=content_type,
    )
