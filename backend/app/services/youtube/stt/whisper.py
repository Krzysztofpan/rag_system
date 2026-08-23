from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

from app.config import get_settings
from app.services.youtube.caption_client import TranscriptCue
from app.services.youtube.stt.errors import YoutubeSttError


@dataclass(frozen=True)
class WhisperResult:
    cues: list[TranscriptCue]
    language: str | None


class OpenAIWhisperTranscriber:
    def __init__(self, *, api_key: str | None = None, model: str = "whisper-1"):
        self._api_key = api_key
        self._model = model

    def transcribe(self, audio_path: Path) -> WhisperResult:
        api_key = self._api_key or get_settings().openai_api_key
        if not api_key:
            raise YoutubeSttError("OPENAI_API_KEY is not set")
        client = OpenAI(api_key=api_key)
        try:
            with audio_path.open("rb") as handle:
                result = client.audio.transcriptions.create(
                    model=self._model,
                    file=handle,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )
        except YoutubeSttError:
            raise
        except Exception as exc:
            raise YoutubeSttError(f"Speech-to-text failed: {exc}") from exc

        cues: list[TranscriptCue] = []
        for segment in getattr(result, "segments", None) or []:
            text = " ".join((getattr(segment, "text", None) or "").split())
            if not text:
                continue
            start = float(getattr(segment, "start", 0.0) or 0.0)
            end = float(getattr(segment, "end", start) or start)
            cues.append(
                TranscriptCue(text=text, start=start, duration=max(end - start, 0.0))
            )
        if not cues:
            text = " ".join((getattr(result, "text", None) or "").split())
            if text:
                cues = [TranscriptCue(text=text, start=0.0, duration=0.0)]
        language = getattr(result, "language", None)
        return WhisperResult(cues=cues, language=language)
