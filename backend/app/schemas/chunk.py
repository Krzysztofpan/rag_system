from uuid import UUID

from app.schemas.base import APIModel


class ChunkResponse(APIModel):
    """An owned document chunk exposed as a citation preview."""

    id: UUID
    document_id: UUID
    filename: str
    content: str
    pages: list[int] | None = None
    chunk_index: int
