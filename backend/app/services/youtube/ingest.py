from __future__ import annotations

import asyncio
from collections.abc import Callable
from uuid import UUID

from app.background_tasks.upload_background import apply_document_summary
from app.config import Settings, get_settings
from app.container import create_document_service, create_indexing_service
from app.db.session import get_session_factory
from app.lib.file_types import FileTypes
from app.lib.tracing import conversation_tracing
from app.schemas.origin import YoutubeOrigin
from app.services.parser.base import ParseResult
from app.services.parser.complex.quality_audit import audit_markdown
from app.services.youtube.caption_client import (
    CaptionClient,
    TranscriptUnavailableError,
    YoutubeTranscript,
)
from app.services.youtube.stt import SpeechToText, YoutubeSttError
from app.services.youtube.title import fetch_youtube_title
from app.services.youtube.transcript_markdown import transcript_to_markdown


TitleFetcher = Callable[[str], str | None]


class YoutubeIngestService:
    def __init__(
        self,
        caption_client: CaptionClient | None = None,
        title_fetcher: TitleFetcher | None = None,
        speech_to_text: SpeechToText | None = None,
        settings: Settings | None = None,
    ):
        self.caption_client = caption_client or CaptionClient()
        self.title_fetcher = title_fetcher or fetch_youtube_title
        self._speech_to_text = speech_to_text
        self.settings = settings or get_settings()

    @property
    def speech_to_text(self) -> SpeechToText:
        if self._speech_to_text is None:
            self._speech_to_text = SpeechToText(settings=self.settings)
        return self._speech_to_text

    async def ingest(
        self,
        *,
        conversation_id: UUID,
        document_id: UUID,
        user_id: UUID,
        url: str,
        video_id: str,
    ) -> None:
        with conversation_tracing(
            conversation_id,
            user_id=user_id,
            tags=["ingest"],
            extra_metadata={"document_id": document_id, "video_id": video_id},
        ):
            try:
                transcript = await self._resolve_transcript(url, video_id)
                title = await asyncio.to_thread(self.title_fetcher, url)
                filename = title or f"youtube:{video_id}"
                markdown = transcript_to_markdown(
                    title=filename,
                    url=url,
                    transcript=transcript,
                )
                duration_sec = None
                if transcript.cues:
                    last = transcript.cues[-1]
                    duration_sec = last.start + last.duration

                session_factory = get_session_factory()
                async with session_factory() as session:
                    document_service = create_document_service(session)
                    indexing = create_indexing_service(session)

                    if title:
                        await document_service.change_document_name(
                            conversation_id,
                            document_id,
                            title,
                            user_id=user_id,
                        )

                    result = await indexing.index_parsed(
                        document_id=document_id,
                        conversation_id=conversation_id,
                        parsed=ParseResult(
                            markdown=markdown,
                            report=audit_markdown(markdown),
                            filename=filename,
                            content_type=FileTypes.YOUTUBE,
                        ),
                        source_filename=filename,
                        content_type=FileTypes.YOUTUBE,
                    )
                    await document_service.update_document_origin(
                        document_id,
                        YoutubeOrigin(
                            video_id=video_id,
                            url=url,
                            duration_sec=duration_sec,
                            language=transcript.language,
                            transcript_source=transcript.source,
                        ),
                    )

                await apply_document_summary(
                    result.parsed_content,
                    conversation_id,
                    document_id,
                    user_id,
                )
            except TranscriptUnavailableError as exc:
                await self._mark_failed(document_id, str(exc))
            except YoutubeSttError as exc:
                await self._mark_failed(document_id, str(exc))
            except Exception as exc:
                await self._mark_failed(document_id, str(exc))
                raise

    async def _resolve_transcript(self, url: str, video_id: str) -> YoutubeTranscript:
        try:
            return await asyncio.to_thread(self.caption_client.fetch, video_id)
        except TranscriptUnavailableError:
            if not self.settings.youtube_stt_enabled:
                raise
            return await asyncio.to_thread(self.speech_to_text.transcribe, url)

    async def _mark_failed(self, document_id: UUID, message: str) -> None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            document_service = create_document_service(session)
            await document_service.mark_failed(document_id, message)
