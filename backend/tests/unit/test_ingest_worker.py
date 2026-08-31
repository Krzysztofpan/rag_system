from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.ingest.queue import DocumentIngestJob, YoutubeIngestJob
from app.workers.ingest import dispatch_ingest_job


async def test_dispatch_document_job():
    job = DocumentIngestJob(
        conversation_id=uuid4(),
        document_id=uuid4(),
        user_id=uuid4(),
        path="/tmp/note.md",
        filename="note.md",
        content_type="text/markdown",
    )
    with patch(
        "app.workers.ingest.run_document_ingest",
        new=AsyncMock(),
    ) as ingest:
        await dispatch_ingest_job(job)

    ingest.assert_awaited_once_with(job)


async def test_dispatch_youtube_job():
    job = YoutubeIngestJob(
        conversation_id=uuid4(),
        document_id=uuid4(),
        user_id=uuid4(),
        url="https://www.youtube.com/watch?v=dQw4w9wgXcQ",
        video_id="dQw4w9wgXcQ",
    )
    with patch(
        "app.workers.ingest.run_youtube_ingest",
        new=AsyncMock(),
    ) as ingest:
        await dispatch_ingest_job(job)

    ingest.assert_awaited_once_with(job)
