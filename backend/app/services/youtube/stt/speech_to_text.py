from __future__ import annotations

import tempfile
from pathlib import Path

from app.config import Settings, get_settings
from app.services.youtube.caption_client import TranscriptCue, YoutubeTranscript
from app.services.youtube.stt.chunking import (
    AudioChunk,
    FfmpegAudioSplitter,
    stitch_chunk_cues,
)
from app.services.youtube.stt.download import YtDlpAudioDownloader
from app.services.youtube.stt.errors import YoutubeSttError, YoutubeVideoTooLongError
from app.services.youtube.stt.whisper import OpenAIWhisperTranscriber


class SpeechToText:
    def __init__(
        self,
        *,
        downloader: YtDlpAudioDownloader | None = None,
        transcriber: OpenAIWhisperTranscriber | None = None,
        splitter: FfmpegAudioSplitter | None = None,
        settings: Settings | None = None,
    ):
        self.settings = settings or get_settings()
        self.downloader = downloader or YtDlpAudioDownloader()
        self.transcriber = transcriber or OpenAIWhisperTranscriber(
            api_key=self.settings.openai_api_key
        )
        self.splitter = splitter or FfmpegAudioSplitter()

    def transcribe(self, url: str) -> YoutubeTranscript:
        max_duration = self.settings.youtube_max_duration_sec
        max_bytes = self.settings.youtube_stt_max_bytes
        chunk_sec = self.settings.youtube_stt_chunk_sec
        overlap_sec = self.settings.youtube_stt_chunk_overlap_sec
        with tempfile.TemporaryDirectory(prefix="youtube-stt-") as tmp:
            tmp_dir = Path(tmp)
            probe = self.downloader.probe(url)
            duration = probe.duration_sec
            if duration is None:
                raise YoutubeSttError(
                    "No captions are available and video duration could not be determined"
                )
            if duration > max_duration:
                minutes = max(1, max_duration // 60)
                raise YoutubeVideoTooLongError(
                    "No captions are available and the video is longer than "
                    f"{minutes} minutes"
                )

            source_dir = tmp_dir / "source"
            audio_path = self.downloader.download(url, source_dir)
            if not audio_path.exists():
                raise YoutubeSttError("Audio download did not produce a file")

            if audio_path.stat().st_size > max_bytes:
                pieces = self.splitter.split(
                    audio_path,
                    tmp_dir / "chunks",
                    duration_sec=duration,
                    chunk_sec=chunk_sec,
                    overlap_sec=overlap_sec,
                )
            else:
                pieces = [AudioChunk(path=audio_path, start_sec=0.0)]

            chunk_results: list[tuple[float, list[TranscriptCue]]] = []
            language: str | None = None
            for piece in pieces:
                if piece.path.stat().st_size > max_bytes:
                    raise YoutubeSttError(
                        "Audio chunk exceeds the speech-to-text size limit"
                    )
                result = self.transcriber.transcribe(piece.path)
                if result.language:
                    language = language or result.language
                chunk_results.append((piece.start_sec, result.cues))

            cues = stitch_chunk_cues(chunk_results, overlap_sec=overlap_sec)
            if not cues:
                raise YoutubeSttError("Speech-to-text returned an empty transcript")
            return YoutubeTranscript(cues=cues, language=language, source="stt")
