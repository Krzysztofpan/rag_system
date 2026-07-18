from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.chunk import Chunk


class DocumentStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Document(SQLModel, table=True):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed')",
            name="documents_status_check",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    filename: str
    content_type: str | None = None
    file_size_bytes: int | None = None
    status: DocumentStatus = Field(default=DocumentStatus.pending)
    error_message: str | None = None
    chunk_count: int = Field(default=0)
    token_count: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    chunks: list["Chunk"] = Relationship(back_populates="document")
