from app.services.youtube.caption_client import TranscriptCue, YoutubeTranscript
from app.services.youtube.transcript_markdown import transcript_to_markdown


def test_transcript_to_markdown_groups_cues_and_uses_headings():
    transcript = YoutubeTranscript(
        cues=[
            TranscriptCue(text="Hello\nthere", start=0.0, duration=2.0),
            TranscriptCue(text="more", start=10.0, duration=2.0),
            TranscriptCue(text="next window", start=35.0, duration=3.0),
        ],
        language="en",
        source="captions",
    )

    markdown = transcript_to_markdown(
        title="Demo video",
        url="https://www.youtube.com/watch?v=dQw4w9wgXcQ",
        transcript=transcript,
    )

    assert markdown.startswith("# Demo video\n")
    assert "Source: https://www.youtube.com/watch?v=dQw4w9wgXcQ" in markdown
    assert "transcript: captions" in markdown
    assert "## 00:00\nHello there more" in markdown
    assert "## 00:35\nnext window" in markdown
