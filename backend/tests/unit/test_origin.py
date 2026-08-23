import pytest
from pydantic import ValidationError

from app.schemas.origin import FileOrigin, YoutubeOrigin, dump_origin, parse_origin


def test_parse_file_origin():
    origin = parse_origin({"kind": "file", "file_size_bytes": 12})
    assert origin == FileOrigin(file_size_bytes=12)


def test_parse_youtube_origin():
    origin = parse_origin(
        {
            "kind": "youtube",
            "video_id": "dQw4w9wgXcQ",
            "url": "https://www.youtube.com/watch?v=dQw4w9wgXcQ",
            "transcript_source": "captions",
        }
    )
    assert isinstance(origin, YoutubeOrigin)
    assert origin.video_id == "dQw4w9wgXcQ"
    assert origin.transcript_source == "captions"


def test_parse_youtube_origin_stt():
    origin = parse_origin(
        {
            "kind": "youtube",
            "video_id": "dQw4w9wgXcQ",
            "url": "https://www.youtube.com/watch?v=dQw4w9wgXcQ",
            "transcript_source": "stt",
        }
    )
    assert isinstance(origin, YoutubeOrigin)
    assert origin.transcript_source == "stt"


def test_parse_origin_none():
    assert parse_origin(None) is None


def test_parse_origin_rejects_unknown_kind():
    with pytest.raises(ValidationError):
        parse_origin({"kind": "web", "url": "https://example.com"})


def test_dump_origin_keeps_snake_case():
    dumped = dump_origin(
        YoutubeOrigin(
            video_id="dQw4w9wgXcQ",
            url="https://youtu.be/dQw4w9wgXcQ",
            language="en",
        )
    )
    assert dumped["video_id"] == "dQw4w9wgXcQ"
    assert "videoId" not in dumped
