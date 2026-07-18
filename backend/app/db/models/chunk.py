from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.document import Document


class Chunk(SQLModel, table=True):
    __tablename__ = "chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    document_id: UUID = Field(foreign_key="documents.id", index=True)
    chunk_index: int
    content: str
    page: int | None = None
    char_start: int | None = None
    char_end: int | None = None
    token_count: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    document: "Document" = Relationship(back_populates="chunks")
