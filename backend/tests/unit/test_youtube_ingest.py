from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.lib.file_types import FileTypes
from app.services.document_indexing_service import IngestResult
from app.services.youtube.caption_client import (
    TranscriptCue,
    TranscriptUnavailableError,
    YoutubeTranscript,
)
from app.services.youtube.ingest import YoutubeIngestService
from app.services.youtube.stt import YoutubeVideoTooLongError


def _transcript(*, source="captions") -> YoutubeTranscript:
    return YoutubeTranscript(
        cues=[
            TranscriptCue(text="Hello", start=0.0, duration=2.0),
            TranscriptCue(text="World", start=2.0, duration=2.0),
        ],
        language="en",
        source=source,
    )


def _settings(*, stt_enabled: bool) -> SimpleNamespace:
    return SimpleNamespace(youtube_stt_enabled=stt_enabled)


def _session_factory():
    session = MagicMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=session_cm)


def _document_service():
    service = MagicMock()
    service.change_document_name = AsyncMock()
    service.update_document_origin = AsyncMock()
    service.mark_failed = AsyncMock()
    return service


def _indexing(document_id):
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
    return indexing


async def _run_ingest(service, *, document_id, document_service, indexing=None):
    summarize = AsyncMock()
    patches = [
        patch(
            "app.services.youtube.ingest.get_session_factory",
            return_value=_session_factory(),
        ),
        patch(
            "app.services.youtube.ingest.create_document_service",
            return_value=document_service,
        ),
    ]
    if indexing is not None:
        patches.append(
            patch(
                "app.services.youtube.ingest.create_indexing_service",
                return_value=indexing,
            )
        )
        patches.append(
            patch(
                "app.services.youtube.ingest.summarize_document_and_update_title",
                new=summarize,
            )
        )
    with ExitStack() as stack:
        for item in patches:
            stack.enter_context(item)
        await service.ingest(
            conversation_id=uuid4(),
            document_id=document_id,
            user_id=uuid4(),
            url="https://www.youtube.com/watch?v=dQw4w9wgXcQ",
            video_id="dQw4w9wgXcQ",
        )
    return summarize


async def test_youtube_ingest_indexes_parsed_transcript():
    caption_client = MagicMock()
    caption_client.fetch.return_value = _transcript()
    speech_to_text = MagicMock()
    document_id = uuid4()
    document_service = _document_service()
    indexing = _indexing(document_id)
    service = YoutubeIngestService(
        caption_client=caption_client,
        title_fetcher=lambda url: "Demo video",
        speech_to_text=speech_to_text,
        settings=_settings(stt_enabled=True),
    )

    summarize = await _run_ingest(
        service,
        document_id=document_id,
        document_service=document_service,
        indexing=indexing,
    )

    speech_to_text.transcribe.assert_not_called()
    document_service.change_document_name.assert_awaited_once()
    parsed = indexing.index_parsed.await_args.kwargs["parsed"]
    assert parsed.content_type == FileTypes.YOUTUBE
    assert parsed.markdown.startswith("# Demo video")
    assert "Hello" in parsed.markdown
    origin = document_service.update_document_origin.await_args.args[1]
    assert origin.video_id == "dQw4w9wgXcQ"
    assert origin.url == "https://www.youtube.com/watch?v=dQw4w9wgXcQ"
    assert origin.transcript_source == "captions"
    assert origin.language == "en"
    assert origin.duration_sec == 4.0
    summarize.assert_awaited_once()


async def test_youtube_ingest_marks_failed_when_captions_missing_and_stt_off():
    caption_client = MagicMock()
    caption_client.fetch.side_effect = TranscriptUnavailableError("No captions")
    speech_to_text = MagicMock()
    document_id = uuid4()
    document_service = _document_service()
    service = YoutubeIngestService(
        caption_client=caption_client,
        title_fetcher=lambda url: None,
        speech_to_text=speech_to_text,
        settings=_settings(stt_enabled=False),
    )

    await _run_ingest(
        service,
        document_id=document_id,
        document_service=document_service,
    )

    speech_to_text.transcribe.assert_not_called()
    document_service.mark_failed.assert_awaited_once()
    assert "No captions" in document_service.mark_failed.await_args.args[1]


async def test_youtube_ingest_indexes_stt_when_captions_missing():
    caption_client = MagicMock()
    caption_client.fetch.side_effect = TranscriptUnavailableError("No captions")
    speech_to_text = MagicMock()
    speech_to_text.transcribe.return_value = _transcript(source="stt")
    document_id = uuid4()
    document_service = _document_service()
    indexing = _indexing(document_id)
    service = YoutubeIngestService(
        caption_client=caption_client,
        title_fetcher=lambda url: "Demo video",
        speech_to_text=speech_to_text,
        settings=_settings(stt_enabled=True),
    )

    summarize = await _run_ingest(
        service,
        document_id=document_id,
        document_service=document_service,
        indexing=indexing,
    )

    speech_to_text.transcribe.assert_called_once_with(
        "https://www.youtube.com/watch?v=dQw4w9wgXcQ"
    )
    origin = document_service.update_document_origin.await_args.args[1]
    assert origin.transcript_source == "stt"
    parsed = indexing.index_parsed.await_args.kwargs["parsed"]
    assert "transcript: stt" in parsed.markdown
    summarize.assert_awaited_once()
    document_service.mark_failed.assert_not_called()


async def test_youtube_ingest_marks_failed_when_stt_video_too_long():
    caption_client = MagicMock()
    caption_client.fetch.side_effect = TranscriptUnavailableError("No captions")
    speech_to_text = MagicMock()
    speech_to_text.transcribe.side_effect = YoutubeVideoTooLongError(
        "No captions are available and the video is longer than 45 minutes"
    )
    document_id = uuid4()
    document_service = _document_service()
    indexing = _indexing(document_id)
    service = YoutubeIngestService(
        caption_client=caption_client,
        title_fetcher=lambda url: None,
        speech_to_text=speech_to_text,
        settings=_settings(stt_enabled=True),
    )

    await _run_ingest(
        service,
        document_id=document_id,
        document_service=document_service,
        indexing=indexing,
    )

    document_service.mark_failed.assert_awaited_once()
    assert "longer than 45 minutes" in document_service.mark_failed.await_args.args[1]
    indexing.index_parsed.assert_not_called()
