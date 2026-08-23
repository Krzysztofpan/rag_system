from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yt_dlp

from app.services.youtube.stt.errors import YoutubeSttError


@dataclass(frozen=True)
class AudioProbe:
    duration_sec: float | None


class YtDlpAudioDownloader:
    def __init__(self, ydl_cls: type = yt_dlp.YoutubeDL):
        self._ydl_cls = ydl_cls

    def _opts(self, extra: dict | None = None) -> dict:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "noprogress": True,
            "socket_timeout": 30,
            "retries": 2,
        }
        if extra:
            opts.update(extra)
        return opts

    def probe(self, url: str) -> AudioProbe:
        try:
            with self._ydl_cls(self._opts({"skip_download": True})) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as exc:
            raise YoutubeSttError(f"Failed to read video metadata: {exc}") from exc
        duration = info.get("duration") if isinstance(info, dict) else None
        if duration is None:
            return AudioProbe(duration_sec=None)
        return AudioProbe(duration_sec=float(duration))

    def download(self, url: str, dest_dir: Path) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        try:
            with self._ydl_cls(
                self._opts(
                    {
                        "format": "bestaudio[ext=m4a]/bestaudio/best",
                        "outtmpl": str(dest_dir / "audio.%(ext)s"),
                        "overwrites": True,
                    }
                )
            ) as ydl:
                ydl.extract_info(url, download=True)
        except Exception as exc:
            raise YoutubeSttError(f"Failed to download audio: {exc}") from exc
        files = sorted(path for path in dest_dir.iterdir() if path.is_file())
        if not files:
            raise YoutubeSttError("Audio download did not produce a file")
        return files[0]
