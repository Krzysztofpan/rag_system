from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.services.youtube.caption_client import TranscriptCue
from app.services.youtube.stt.errors import YoutubeSttError


@dataclass(frozen=True)
class AudioChunk:
    path: Path
    start_sec: float


def chunk_windows(
    duration_sec: float,
    chunk_sec: float,
    overlap_sec: float,
) -> list[tuple[float, float]]:
    if duration_sec <= 0:
        return []
    if duration_sec <= chunk_sec:
        return [(0.0, duration_sec)]
    step = chunk_sec - overlap_sec
    if step <= 0:
        raise ValueError("chunk_sec must be greater than overlap_sec")
    windows: list[tuple[float, float]] = []
    start = 0.0
    while start < duration_sec:
        length = min(chunk_sec, duration_sec - start)
        windows.append((start, length))
        if start + length >= duration_sec:
            break
        start += step
    return windows


def stitch_chunk_cues(
    chunks: list[tuple[float, list[TranscriptCue]]],
    overlap_sec: float,
) -> list[TranscriptCue]:
    merged: list[TranscriptCue] = []
    for index, (offset, cues) in enumerate(chunks):
        cutoff = 0.0 if index == 0 else offset + overlap_sec
        for cue in cues:
            abs_start = offset + cue.start
            if abs_start + 1e-6 < cutoff:
                continue
            text = " ".join(cue.text.split())
            if not text:
                continue
            merged.append(
                TranscriptCue(text=text, start=abs_start, duration=cue.duration)
            )
    return merged


class FfmpegAudioSplitter:
    def split(
        self,
        audio_path: Path,
        dest_dir: Path,
        *,
        duration_sec: float,
        chunk_sec: float,
        overlap_sec: float,
    ) -> list[AudioChunk]:
        dest_dir.mkdir(parents=True, exist_ok=True)
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise YoutubeSttError(
                "ffmpeg is required to prepare audio for speech-to-text"
            )
        chunks: list[AudioChunk] = []
        for index, (start, length) in enumerate(
            chunk_windows(duration_sec, chunk_sec, overlap_sec)
        ):
            output = dest_dir / f"chunk_{index:03d}.mp3"
            command = [
                ffmpeg,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                str(start),
                "-t",
                str(length),
                "-i",
                str(audio_path),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-b:a",
                "64k",
                str(output),
            ]
            try:
                subprocess.run(command, check=True, capture_output=True, text=True)
            except FileNotFoundError as exc:
                raise YoutubeSttError(
                    "ffmpeg is required to prepare audio for speech-to-text"
                ) from exc
            except subprocess.CalledProcessError as exc:
                detail = (exc.stderr or exc.stdout or "ffmpeg failed").strip()
                raise YoutubeSttError(
                    f"Failed to split audio for speech-to-text: {detail}"
                ) from exc
            chunks.append(AudioChunk(path=output, start_sec=start))
        return chunks
