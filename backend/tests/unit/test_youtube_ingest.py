from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.lib.file_types import FileTypes
from app.services.document_indexing_service import IngestResult
from app.services.youtube.caption_client import (
    TranscriptCue,
    TranscriptUnavailableError,
    YoutubeTranscript,
)
from app.services.youtube.ingest import YoutubeIngestService


def _transcript() -> YoutubeTranscript:
    return YoutubeTranscript(
        cues=[
            TranscriptCue(text="Hello", start=0.0, duration=2.0),
            TranscriptCue(text="World", start=2.0, duration=2.0),
        ],
        language="en",
        source="captions",
    )


@pytest.fixture
def caption_client():
    client = MagicMock()
    client.fetch.return_value = _transcript()
    return client


async def test_youtube_ingest_indexes_parsed_transcript(caption_client):
    conversation_id = uuid4()
    document_id = uuid4()
    user_id = uuid4()

    document_service = MagicMock()
    document_service.change_document_name = AsyncMock()
    document_service.update_document_origin = AsyncMock()
    indexing = MagicMock()
    indexing.index_parsed = AsyncMock(
        return_value=IngestResult(
            document_id=document_id,
            parsed_content="# Title\n\nHello World\n",
            chunk_ids=[uuid4()],
            parse_report={"ok": True, "counts": {}, "issues": []},
            chunk_quality={
                "ok": True,
                "total_chunks": 1,
                "kept_chunks": 1,
                "rejected_chunks": 0,
                "rejected_ratio": 0.0,
                "max_rejected_ratio": 0.25,
                "rejected": [],
                "kept_indexes": [0],
            },
        )
    )

    session = MagicMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    session_factory = MagicMock(return_value=session_cm)

    service = YoutubeIngestService(
        caption_client=caption_client,
        title_fetcher=lambda url: "Demo video",
    )

    with (
        patch(
            "app.services.youtube.ingest.get_session_factory",
            return_value=session_factory,
        ),
        patch(
            "app.services.youtube.ingest.create_document_service",
            return_value=document_service,
        ),
        patch(
            "app.services.youtube.ingest.create_indexing_service",
            return_value=indexing,
        ),
        patch(
            "app.services.youtube.ingest.summarize_document_and_update_title",
            new=AsyncMock(),
        ) as summarize,
    ):
        await service.ingest(
            conversation_id=conversation_id,
            document_id=document_id,
            user_id=user_id,
            url="https://www.youtube.com/watch?v=dQw4w9wgXcQ",
            video_id="dQw4w9wgXcQ",
        )

    document_service.change_document_name.assert_awaited_once()
    parsed = indexing.index_parsed.await_args.kwargs["parsed"]
    assert parsed.content_type == FileTypes.YOUTUBE
    assert parsed.markdown.startswith("# Demo video")
    assert "Hello World" in parsed.markdown or "Hello" in parsed.markdown
    origin = document_service.update_document_origin.await_args.args[1]
    assert origin.video_id == "dQw4w9wgXcQ"
    assert origin.url == "https://www.youtube.com/watch?v=dQw4w9wgXcQ"
    assert origin.transcript_source == "captions"
    assert origin.language == "en"
    assert origin.duration_sec == 4.0
    summarize.assert_awaited_once()


async def test_youtube_ingest_marks_failed_when_captions_missing(caption_client):
    caption_client.fetch.side_effect = TranscriptUnavailableError("No captions")
    document_id = uuid4()

    document_service = MagicMock()
    document_service.mark_failed = AsyncMock()

    session = MagicMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)

    service = YoutubeIngestService(
        caption_client=caption_client,
        title_fetcher=lambda url: None,
    )

    with (
        patch(
            "app.services.youtube.ingest.get_session_factory",
            return_value=MagicMock(return_value=session_cm),
        ),
        patch(
            "app.services.youtube.ingest.create_document_service",
            return_value=document_service,
        ),
    ):
        await service.ingest(
            conversation_id=uuid4(),
            document_id=document_id,
            user_id=uuid4(),
            url="https://www.youtube.com/watch?v=dQw4w9wgXcQ",
            video_id="dQw4w9wgXcQ",
        )

    document_service.mark_failed.assert_awaited_once()
    assert "No captions" in document_service.mark_failed.await_args.args[1]
