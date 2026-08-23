from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from youtube_transcript_api import (
    AgeRestricted,
    InvalidVideoId,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
    YouTubeTranscriptApi,
)


class TranscriptUnavailableError(Exception):
    """Video has no usable captions (manual or auto)."""


@dataclass(frozen=True)
class TranscriptCue:
    text: str
    start: float
    duration: float


@dataclass(frozen=True)
class YoutubeTranscript:
    cues: list[TranscriptCue]
    language: str | None
    source: Literal["captions", "auto_captions"]


class CaptionClient:
    def __init__(self, api: YouTubeTranscriptApi | None = None):
        self._api = api or YouTubeTranscriptApi()

    def fetch(self, video_id: str) -> YoutubeTranscript:
        try:
            transcript_list = self._api.list(video_id)
        except (
            TranscriptsDisabled,
            NoTranscriptFound,
            VideoUnavailable,
            VideoUnplayable,
            AgeRestricted,
            InvalidVideoId,
        ) as exc:
            raise TranscriptUnavailableError(str(exc)) from exc

        transcripts = list(transcript_list)
        if not transcripts:
            raise TranscriptUnavailableError("No captions are available for this video")

        # Prefer manually created captions; fall back to the first listed track (usually auto).
        chosen = next(
            (item for item in transcripts if not item.is_generated),
            transcripts[0],
        )
        try:
            fetched = chosen.fetch()
        except (TranscriptsDisabled, NoTranscriptFound) as exc:
            raise TranscriptUnavailableError(str(exc)) from exc

        cues = [
            TranscriptCue(text=snippet.text, start=snippet.start, duration=snippet.duration)
            for snippet in fetched
            if snippet.text.strip()
        ]
        if not cues:
            raise TranscriptUnavailableError("Captions for this video are empty")

        return YoutubeTranscript(
            cues=cues,
            language=fetched.language_code,
            source="auto_captions" if fetched.is_generated else "captions",
        )
