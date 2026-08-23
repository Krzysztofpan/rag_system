import re
from dataclasses import dataclass
from urllib.parse import urlparse

# Same pattern pytube uses: ID after v= or a slash. Host is checked separately
# so a random site with ?v=11chars is rejected.
_VIDEO_ID_IN_URL = re.compile(r"(?:v=|/)([0-9A-Za-z_-]{11})")
_YOUTUBE_HOST = re.compile(
    r"^(?:[\w-]+\.)*(?:youtube(?:-nocookie)?\.com|youtu\.be)$"
)


class InvalidYoutubeUrlError(ValueError):
    """URL is not a single YouTube video."""


@dataclass(frozen=True)
class YoutubeVideoRef:
    video_id: str
    url: str


def parse_youtube_url(url: str) -> YoutubeVideoRef:
    raw = _with_http_scheme((url or "").strip())
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        raise InvalidYoutubeUrlError("URL must be an http(s) YouTube link")

    host = parsed.netloc.lower().split(":", 1)[0]
    if _YOUTUBE_HOST.fullmatch(host) is None:
        raise InvalidYoutubeUrlError("Only YouTube video URLs are supported")

    match = _VIDEO_ID_IN_URL.search(raw)
    if match is None:
        raise InvalidYoutubeUrlError("Could not find a YouTube video id in the URL")
    video_id = match.group(1)

    return YoutubeVideoRef(video_id=video_id, url=raw)


def _with_http_scheme(url: str) -> str:
    if not url or "://" in url:
        return url
    if url.startswith("//"):
        return f"https:{url}"
    return f"https://{url}"
