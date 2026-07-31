from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.chunker.complex import ComplexChunker
from app.types import FileTypes


def test_resolve_offsets_finds_substring_and_advances_search():
    chunker = ComplexChunker(FileTypes.PDF)
    markdown = "aaa hello world hello again"
    start, end, nxt = chunker.resolve_offsets("hello", markdown, 0)
    assert (start, end) == (4, 9)
    start2, end2, _ = chunker.resolve_offsets("hello", markdown, nxt)
    assert (start2, end2) == (16, 21)


def test_resolve_offsets_returns_none_when_missing():
    chunker = ComplexChunker(FileTypes.PDF)
    start, end, nxt = chunker.resolve_offsets("missing", "present text", 0)
    assert start is None and end is None
    assert nxt == 0


def test_get_pages_dedupes_and_preserves_order():
    chunker = ComplexChunker(FileTypes.PDF)
    chunk = SimpleNamespace(
        meta=SimpleNamespace(
            doc_items=[
                SimpleNamespace(prov=[SimpleNamespace(page_no=2), SimpleNamespace(page_no=2)]),
                SimpleNamespace(prov=[SimpleNamespace(page_no=5)]),
            ]
        )
    )
    assert chunker.get_pages(chunk) == [2, 5]


def test_generate_context_strips_body_and_delimiter():
    chunker = ComplexChunker(FileTypes.PDF)
    chunker.text_splitter = MagicMock()
    chunker.text_splitter.delim = "\n"
    chunker.text_splitter.contextualize.return_value = "Heading\n\nbody text"
    chunk = SimpleNamespace(text="body text")

    assert chunker.generate_context(chunk) == "Heading"


def test_complex_chunker_chunk_uses_hybrid_chunker_output():
    chunker = ComplexChunker(FileTypes.PDF)
    markdown = "Section one text here."

    fake_chunk = SimpleNamespace(
        text="Section one text here.",
        meta=SimpleNamespace(
            doc_items=[SimpleNamespace(prov=[SimpleNamespace(page_no=1)])]
        ),
    )

    hybrid = MagicMock()
    hybrid.chunk.return_value = [fake_chunk]
    hybrid.contextualize.return_value = "H1\n\nSection one text here."
    hybrid.delim = "\n\n"
    chunker.text_splitter = hybrid

    fake_doc = object()
    results = chunker._chunk(doc=fake_doc, source_text=markdown)

    hybrid.chunk.assert_called_once_with(dl_doc=fake_doc)
    assert len(results) == 1
    assert results[0].content == "Section one text here."
    assert results[0].context == "H1"
    assert results[0].pages == [1]
    assert results[0].char_start == 0
    assert results[0].char_end == len(markdown)
    assert results[0].token_count and results[0].token_count > 0
