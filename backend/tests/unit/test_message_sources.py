from uuid import uuid4

import pytest
from langchain_core.documents import Document
from pydantic import ValidationError

from app.agent.sources import build_source, cite_documents, cite_excerpt
from app.schemas.message_source import dump_message_sources
from app.services.security.spotlighting import (
    UNTRUSTED_DOCUMENT_END,
    UNTRUSTED_DOCUMENT_START,
)


def test_build_source_returns_pointer_without_mutating():
    chunk_id = uuid4()
    document_id = uuid4()

    chunk = build_source(kind="chunk", index=1, chunk_id=chunk_id)
    summary = build_source(kind="summary", index=2, document_id=document_id)
    web = build_source(kind="web", index=3, url="https://example.com")

    assert chunk == {"index": 1, "kind": "chunk", "chunk_id": str(chunk_id)}
    assert summary == {
        "index": 2,
        "kind": "summary",
        "document_id": str(document_id),
    }
    assert web == {"index": 3, "kind": "web", "url": "https://example.com"}


def test_cite_excerpt_appends_source_and_wraps_header():
    context: dict = {"sources": []}
    document_id = uuid4()

    wrapped = cite_excerpt(
        context,
        "safe overview",
        header="Summary",
        kind="summary",
        document_id=document_id,
    )

    assert wrapped.startswith("[1] Summary")
    assert "safe overview" in wrapped
    assert context["sources"] == [
        {"index": 1, "kind": "summary", "document_id": str(document_id)},
    ]


@pytest.mark.parametrize(
    ("kind", "kwargs", "message"),
    [
        ("chunk", {}, "chunk sources require chunk_id"),
        ("summary", {}, "summary sources require document_id"),
        ("web", {}, "web sources require url"),
    ],
)
def test_build_source_requires_openable_pointer(kind, kwargs, message):
    with pytest.raises(ValueError, match=message):
        build_source(kind=kind, index=1, **kwargs)


def test_cite_documents_continues_numbering_and_skips_unopenable_source():
    context: dict = {
        "sources": [
            {"index": 1, "kind": "web", "url": "https://example.com"},
        ]
    }
    documents = [
        Document(
            page_content="found stack",
            metadata={"chunk_id": "a", "document_id": "d1", "pages": [1]},
        ),
        Document(page_content="fallback without pointer"),
    ]

    formatted = cite_documents(context, documents, {"d1": "stack.md"})

    assert formatted.startswith("[2] stack.md, p. 1")
    assert (
        f"{UNTRUSTED_DOCUMENT_START}\nfound stack\n{UNTRUSTED_DOCUMENT_END}"
        in formatted
    )
    assert "[3]" not in formatted
    assert "fallback without pointer" in formatted
    assert context["sources"] == [
        {"index": 1, "kind": "web", "url": "https://example.com"},
        {"index": 2, "kind": "chunk", "chunk_id": "a"},
    ]


def test_dump_message_sources_uses_storage_field_names_by_default():
    chunk_id = uuid4()
    dumped = dump_message_sources(
        [{"index": 1, "kind": "chunk", "chunk_id": str(chunk_id)}]
    )

    assert dumped == [
        {"index": 1, "kind": "chunk", "chunk_id": str(chunk_id)},
    ]
    assert "chunkId" not in dumped[0]


def test_dump_message_sources_uses_camel_case_when_requested():
    chunk_id = uuid4()
    dumped = dump_message_sources(
        [{"index": 1, "kind": "chunk", "chunk_id": str(chunk_id)}],
        by_alias=True,
    )

    assert dumped == [
        {"index": 1, "kind": "chunk", "chunkId": str(chunk_id)},
    ]


def test_dump_message_sources_rejects_unknown_kind():
    with pytest.raises(ValidationError):
        dump_message_sources([{"index": 1, "kind": "file", "chunk_id": str(uuid4())}])
