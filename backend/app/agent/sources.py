from typing import Any, Literal, TypedDict, cast
from uuid import UUID

from langchain_core.documents import Document

from app.services.security import join_untrusted_context, wrap_untrusted_excerpt

SourceKind = Literal["chunk", "summary", "web"]


class ChunkSource(TypedDict):
    index: int
    kind: Literal["chunk"]
    chunk_id: str


class SummarySource(TypedDict):
    index: int
    kind: Literal["summary"]
    document_id: str


class WebSource(TypedDict):
    index: int
    kind: Literal["web"]
    url: str


MessageSource = ChunkSource | SummarySource | WebSource
SourceContext = dict[str, Any]


def sources_from_context(context: SourceContext) -> list[MessageSource]:
    """Return the shared per-turn source registry."""
    return cast(list[MessageSource], context.setdefault("sources", []))


def build_source(
    *,
    index: int,
    kind: SourceKind,
    chunk_id: UUID | str | None = None,
    document_id: UUID | str | None = None,
    url: str | None = None,
) -> MessageSource:
    """Build a citation pointer. The caller appends it to the turn's sources."""
    if kind == "chunk":
        if chunk_id is None:
            raise ValueError("chunk sources require chunk_id")
        return {"index": index, "kind": "chunk", "chunk_id": str(chunk_id)}
    if kind == "summary":
        if document_id is None:
            raise ValueError("summary sources require document_id")
        return {
            "index": index,
            "kind": "summary",
            "document_id": str(document_id),
        }
    if not url:
        raise ValueError("web sources require url")
    return {"index": index, "kind": "web", "url": url}


def cite_excerpt(
    context: dict[str, Any],
    text: str,
    *,
    header: str,
    kind: SourceKind,
    chunk_id: UUID | str | None = None,
    document_id: UUID | str | None = None,
    url: str | None = None,
) -> str:
    """Append a turn source and wrap the excerpt with a [n] header."""
    sources = sources_from_context(context)
    source = build_source(
        index=len(sources) + 1,
        kind=kind,
        chunk_id=chunk_id,
        document_id=document_id,
        url=url,
    )
    sources.append(source)
    return wrap_untrusted_excerpt(text, header=f"[{source['index']}] {header}")


def _pages_suffix(pages: object) -> str:
    if not isinstance(pages, list) or not pages:
        return ""
    return f", p. {', '.join(str(page) for page in pages)}"


def cite_documents(
    context: SourceContext,
    documents: list[Document],
    filenames: dict[str, str],
) -> str:
    """Format retrieved chunks and register pointers that can be opened."""
    excerpts: list[str] = []
    for document in documents:
        metadata = document.metadata or {}
        filename = filenames.get(str(metadata.get("document_id")), "document")
        header = f"{filename}{_pages_suffix(metadata.get('pages'))}"
        chunk_id = metadata.get("chunk_id")
        if chunk_id:
            excerpts.append(
                cite_excerpt(
                    context,
                    document.page_content,
                    header=header,
                    kind="chunk",
                    chunk_id=chunk_id,
                )
            )
        else:
            excerpts.append(
                wrap_untrusted_excerpt(document.page_content, header=header)
            )
    return join_untrusted_context(excerpts)
