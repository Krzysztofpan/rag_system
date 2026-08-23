from uuid import UUID

from app.services.youtube.ingest import YoutubeIngestService


async def ingest_youtube_source(
    conversation_id: UUID,
    document_id: UUID,
    user_id: UUID,
    url: str,
    video_id: str,
) -> None:
    await YoutubeIngestService().ingest(
        conversation_id=conversation_id,
        document_id=document_id,
        user_id=user_id,
        url=url,
        video_id=video_id,
    )
