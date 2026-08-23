from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled

from app.services.youtube.caption_client import (
    CaptionClient,
    TranscriptUnavailableError,
)


class FakeFetched:
    def __init__(self, snippets, *, language_code="en", is_generated=False):
        self.language_code = language_code
        self.is_generated = is_generated
        self._snippets = snippets

    def __iter__(self):
        return iter(self._snippets)


def _listed_transcript(*, is_generated: bool, snippets, language_code="en"):
    fetched = FakeFetched(
        snippets,
        language_code=language_code,
        is_generated=is_generated,
    )
    item = SimpleNamespace(
        is_generated=is_generated,
        fetch=MagicMock(return_value=fetched),
    )
    return item


def test_caption_client_prefers_manual_captions():
    snippets = [SimpleNamespace(text="hello", start=0.0, duration=1.5)]
    auto = _listed_transcript(is_generated=True, snippets=snippets)
    manual = _listed_transcript(is_generated=False, snippets=snippets)
    api = MagicMock()
    api.list.return_value = [auto, manual]

    result = CaptionClient(api).fetch("abc")

    assert result.source == "captions"
    assert result.language == "en"
    assert result.cues[0].text == "hello"
    manual.fetch.assert_called_once()
    auto.fetch.assert_not_called()


def test_caption_client_falls_back_to_auto_captions():
    snippets = [SimpleNamespace(text="auto text", start=1.0, duration=2.0)]
    auto = _listed_transcript(
        is_generated=True,
        snippets=snippets,
        language_code="pl",
    )
    api = MagicMock()
    api.list.return_value = [auto]

    result = CaptionClient(api).fetch("abc")

    assert result.source == "auto_captions"
    assert result.language == "pl"
    auto.fetch.assert_called_once()


def test_caption_client_raises_when_transcripts_disabled():
    api = MagicMock()
    api.list.side_effect = TranscriptsDisabled("abc")

    with pytest.raises(TranscriptUnavailableError):
        CaptionClient(api).fetch("abc")


def test_caption_client_raises_when_list_empty():
    api = MagicMock()
    api.list.return_value = []

    with pytest.raises(TranscriptUnavailableError, match="No captions"):
        CaptionClient(api).fetch("abc")


def test_caption_client_raises_when_fetch_finds_nothing():
    item = SimpleNamespace(
        is_generated=False,
        fetch=MagicMock(
            side_effect=NoTranscriptFound("abc", [], SimpleNamespace()),
        ),
    )
    api = MagicMock()
    api.list.return_value = [item]

    with pytest.raises(TranscriptUnavailableError):
        CaptionClient(api).fetch("abc")
