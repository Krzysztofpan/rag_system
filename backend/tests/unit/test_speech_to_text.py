from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.youtube.caption_client import TranscriptCue
from app.services.youtube.stt.chunking import (
    AudioChunk,
    chunk_windows,
    stitch_chunk_cues,
)
from app.services.youtube.stt.download import AudioProbe, YtDlpAudioDownloader
from app.services.youtube.stt.errors import YoutubeSttError, YoutubeVideoTooLongError
from app.services.youtube.stt.speech_to_text import SpeechToText
from app.services.youtube.stt.whisper import OpenAIWhisperTranscriber, WhisperResult


def _settings(
    *,
    max_duration_sec: int = 2700,
    max_bytes: int = 24 * 1024 * 1024,
    chunk_sec: int = 540,
    overlap_sec: int = 15,
) -> SimpleNamespace:
    return SimpleNamespace(
        youtube_max_duration_sec=max_duration_sec,
        youtube_stt_max_bytes=max_bytes,
        youtube_stt_chunk_sec=chunk_sec,
        youtube_stt_chunk_overlap_sec=overlap_sec,
        openai_api_key="sk-test",
    )


class RecordingDownloader:
    def __init__(self, *, duration_sec: float | None = 12.0, payload: bytes = b"audio"):
        self.duration_sec = duration_sec
        self.payload = payload
        self.dest_dir: Path | None = None
        self.download_calls = 0

    def probe(self, url: str) -> AudioProbe:
        return AudioProbe(duration_sec=self.duration_sec)

    def download(self, url: str, dest_dir: Path) -> Path:
        self.download_calls += 1
        self.dest_dir = dest_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / "audio.m4a"
        path.write_bytes(self.payload)
        return path


def test_chunk_windows_keeps_short_audio_whole():
    assert chunk_windows(10, chunk_sec=540, overlap_sec=15) == [(0.0, 10)]


def test_chunk_windows_overlaps_long_audio():
    windows = chunk_windows(1200, chunk_sec=540, overlap_sec=15)
    assert windows == [(0.0, 540.0), (525.0, 540.0), (1050.0, 150.0)]


def test_stitch_chunk_cues_drops_overlap_from_later_chunks():
    cues = stitch_chunk_cues(
        [
            (0.0, [TranscriptCue(text="one", start=0.0, duration=1.0)]),
            (
                525.0,
                [
                    TranscriptCue(text="overlap", start=10.0, duration=1.0),
                    TranscriptCue(text="two", start=20.0, duration=1.0),
                ],
            ),
        ],
        overlap_sec=15,
    )
    assert [cue.text for cue in cues] == ["one", "two"]
    assert cues[1].start == 545.0


def test_speech_to_text_rejects_too_long_video_before_download():
    downloader = RecordingDownloader(duration_sec=4000)
    transcriber = MagicMock()
    stt = SpeechToText(
        downloader=downloader,
        transcriber=transcriber,
        settings=_settings(max_duration_sec=2700),
    )

    with pytest.raises(YoutubeVideoTooLongError, match="longer than 45 minutes"):
        stt.transcribe("https://youtu.be/abc")

    assert downloader.download_calls == 0
    transcriber.transcribe.assert_not_called()


def test_speech_to_text_rejects_unknown_duration_before_download():
    downloader = RecordingDownloader(duration_sec=None)
    stt = SpeechToText(
        downloader=downloader,
        transcriber=MagicMock(),
        settings=_settings(),
    )

    with pytest.raises(YoutubeSttError, match="duration could not be determined"):
        stt.transcribe("https://youtu.be/abc")

    assert downloader.download_calls == 0


def test_speech_to_text_returns_stt_transcript_and_deletes_audio():
    downloader = RecordingDownloader()
    transcriber = MagicMock()
    transcriber.transcribe.return_value = WhisperResult(
        cues=[TranscriptCue(text="hello", start=0.0, duration=1.2)],
        language="en",
    )
    splitter = MagicMock()
    stt = SpeechToText(
        downloader=downloader,
        transcriber=transcriber,
        splitter=splitter,
        settings=_settings(),
    )

    result = stt.transcribe("https://youtu.be/abc")

    assert result.source == "stt"
    assert result.language == "en"
    assert result.cues[0].text == "hello"
    splitter.split.assert_not_called()
    assert downloader.dest_dir is not None
    assert not downloader.dest_dir.exists()
    assert not downloader.dest_dir.parent.exists()


def test_speech_to_text_deletes_audio_after_error():
    downloader = RecordingDownloader()
    transcriber = MagicMock()
    transcriber.transcribe.side_effect = RuntimeError("whisper down")
    stt = SpeechToText(
        downloader=downloader,
        transcriber=transcriber,
        settings=_settings(),
    )

    with pytest.raises(RuntimeError, match="whisper down"):
        stt.transcribe("https://youtu.be/abc")

    assert downloader.dest_dir is not None
    assert not downloader.dest_dir.exists()
    assert not downloader.dest_dir.parent.exists()


def test_speech_to_text_splits_when_file_exceeds_whisper_limit():
    downloader = RecordingDownloader(payload=b"x" * 20)
    transcriber = MagicMock()
    transcriber.transcribe.side_effect = [
        WhisperResult(
            cues=[TranscriptCue(text="one", start=0.0, duration=1.0)],
            language="en",
        ),
        WhisperResult(
            cues=[
                TranscriptCue(text="overlap", start=10.0, duration=1.0),
                TranscriptCue(text="two", start=20.0, duration=1.0),
            ],
            language="en",
        ),
    ]

    def split(audio_path, dest_dir, *, duration_sec, chunk_sec, overlap_sec):
        dest_dir.mkdir(parents=True, exist_ok=True)
        first = dest_dir / "c0.mp3"
        second = dest_dir / "c1.mp3"
        first.write_bytes(b"a")
        second.write_bytes(b"b")
        return [
            AudioChunk(path=first, start_sec=0.0),
            AudioChunk(path=second, start_sec=525.0),
        ]

    splitter = MagicMock()
    splitter.split.side_effect = split
    stt = SpeechToText(
        downloader=downloader,
        transcriber=transcriber,
        splitter=splitter,
        settings=_settings(max_bytes=10),
    )

    result = stt.transcribe("https://youtu.be/abc")

    splitter.split.assert_called_once()
    assert [cue.text for cue in result.cues] == ["one", "two"]
    assert result.cues[1].start == 545.0
    assert downloader.dest_dir is not None
    assert not downloader.dest_dir.parent.exists()


def test_speech_to_text_rejects_empty_transcript():
    downloader = RecordingDownloader()
    transcriber = MagicMock()
    transcriber.transcribe.return_value = WhisperResult(cues=[], language="en")
    stt = SpeechToText(
        downloader=downloader,
        transcriber=transcriber,
        settings=_settings(),
    )

    with pytest.raises(YoutubeSttError, match="empty transcript"):
        stt.transcribe("https://youtu.be/abc")


def test_whisper_transcriber_maps_segments(tmp_path):
    audio = tmp_path / "audio.m4a"
    audio.write_bytes(b"x")
    fake_client = MagicMock()
    fake_client.audio.transcriptions.create.return_value = SimpleNamespace(
        segments=[SimpleNamespace(text=" hello ", start=1.0, end=3.5)],
        language="en",
        text="hello",
    )
    transcriber = OpenAIWhisperTranscriber(api_key="sk-test")

    with patch(
        "app.services.youtube.stt.whisper.OpenAI",
        return_value=fake_client,
    ):
        result = transcriber.transcribe(audio)

    assert result.language == "en"
    assert result.cues[0].text == "hello"
    assert result.cues[0].start == 1.0
    assert result.cues[0].duration == 2.5


def test_ytdlp_downloader_writes_audio_and_reads_duration(tmp_path):
    class FakeYdl:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=False):
            if download:
                path = self.opts["outtmpl"].replace("%(ext)s", "m4a")
                Path(path).write_bytes(b"audio")
            return {"duration": 99}

    downloader = YtDlpAudioDownloader(ydl_cls=FakeYdl)

    assert downloader.probe("https://youtu.be/abc").duration_sec == 99.0
    path = downloader.download("https://youtu.be/abc", tmp_path)
    assert path.read_bytes() == b"audio"
