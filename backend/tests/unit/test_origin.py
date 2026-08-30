from app.schemas.origin import YoutubeOrigin, dump_origin


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
