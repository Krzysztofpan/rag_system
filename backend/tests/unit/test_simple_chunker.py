from app.services.chunker.simple import SimpleChunker
from app.types import FileTypes


def test_simple_chunker_splits_markdown_with_offsets_and_no_context():
    text = "\n".join(
        [
            "# Intro",
            "",
            "First paragraph about retrieval augmented generation.",
            "",
            "## Details",
            "",
            "Second paragraph with more indexing details for the chunker.",
        ]
    )
    chunker = SimpleChunker(FileTypes.MD)
    chunks = chunker._chunk(doc=text, source_text=text)

    assert chunks
    assert all(chunk.context is None for chunk in chunks)
    assert all(chunk.pages is None for chunk in chunks)
    assert all(chunk.token_count and chunk.token_count > 0 for chunk in chunks)
    assert all(
        chunk.char_start is not None
        and chunk.char_end is not None
        and chunk.char_start < chunk.char_end
        for chunk in chunks
    )
    joined = "".join(chunk.content for chunk in chunks)
    # Recursive splitter keeps separators; content should cover source.
    assert "First paragraph" in joined
    assert "Second paragraph" in joined


def test_simple_chunker_works_for_plain_text():
    text = "Alpha beta gamma. " * 40
    chunker = SimpleChunker(FileTypes.TXT)
    chunks = chunker._chunk(doc=text, source_text=text)
    assert len(chunks) >= 1
    assert chunks[0].char_start == 0
