import pytest

from app.lib.youtube_url import InvalidYoutubeUrlError, parse_youtube_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9wgXcQ",
        "http://youtube.com/watch?v=dQw4w9wgXcQ&t=12s",
        "https://youtu.be/dQw4w9wgXcQ",
        "https://www.youtube.com/shorts/dQw4w9wgXcQ",
        "https://www.youtube.com/embed/dQw4w9wgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9wgXcQ",
        "https://www.youtube-nocookie.com/embed/dQw4w9wgXcQ",
        "www.youtube.com/watch?v=dQw4w9wgXcQ",
        "youtube.com/watch?v=dQw4w9wgXcQ",
        "youtu.be/dQw4w9wgXcQ",
        "//www.youtube.com/watch?v=dQw4w9wgXcQ",
    ],
)
def test_parse_youtube_url_extracts_video_id(url):
    parsed = parse_youtube_url(url)
    assert parsed.video_id == "dQw4w9wgXcQ"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://www.youtube.com/watch?v=dQw4w9wgXcQ",
            "https://www.youtube.com/watch?v=dQw4w9wgXcQ",
        ),
        (
            "http://youtube.com/watch?v=dQw4w9wgXcQ&t=12s",
            "http://youtube.com/watch?v=dQw4w9wgXcQ&t=12s",
        ),
        ("youtu.be/dQw4w9wgXcQ", "https://youtu.be/dQw4w9wgXcQ"),
        (
            "www.youtube.com/watch?v=dQw4w9wgXcQ",
            "https://www.youtube.com/watch?v=dQw4w9wgXcQ",
        ),
        (
            "//www.youtube.com/watch?v=dQw4w9wgXcQ",
            "https://www.youtube.com/watch?v=dQw4w9wgXcQ",
        ),
    ],
)
def test_parse_youtube_url_keeps_user_url(url, expected):
    assert parse_youtube_url(url).url == expected


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not-a-url",
        "https://example.com/watch?v=dQw4w9wgXcQ",
        "https://www.youtube.com/playlist?list=PLxxxxxxxx",
        "https://www.youtube.com/watch?list=PLxxxxxxxx",
        "ftp://www.youtube.com/watch?v=dQw4w9wgXcQ",
    ],
)
def test_parse_youtube_url_rejects_invalid(url):
    with pytest.raises(InvalidYoutubeUrlError):
        parse_youtube_url(url)
