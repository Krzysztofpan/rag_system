from typing import Any, Literal, TypedDict

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
    title: str


MessageSource = ChunkSource | SummarySource | WebSource
SourceContext = dict[str, Any]
