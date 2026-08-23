from __future__ import annotations

from app.services.youtube.caption_client import YoutubeTranscript

_WINDOW_SECONDS = 30.0


def transcript_to_markdown(
    *,
    title: str,
    url: str,
    transcript: YoutubeTranscript,
) -> str:
    lines = [
        f"# {title}",
        f"Source: {url}",
        (
            f"Language: {transcript.language or 'unknown'} · "
            f"transcript: {transcript.source}"
        ),
        "",
    ]

    window_start: float | None = None
    window_parts: list[str] = []

    def flush() -> None:
        if window_start is None or not window_parts:
            return
        lines.append(f"## {_format_timestamp(window_start)}")
        lines.append(" ".join(window_parts).strip())
        lines.append("")

    for cue in transcript.cues:
        text = " ".join(cue.text.split())
        if not text:
            continue
        if window_start is None or cue.start - window_start >= _WINDOW_SECONDS:
            flush()
            window_start = cue.start
            window_parts = [text]
        else:
            window_parts.append(text)

    flush()
    return "\n".join(lines).strip() + "\n"


def _format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
