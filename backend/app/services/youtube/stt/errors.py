class YoutubeSttError(Exception):
    """Speech-to-text fallback failed."""


class YoutubeVideoTooLongError(YoutubeSttError):
    """Video exceeds the configured STT duration limit."""
