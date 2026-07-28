from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, DateTime, Enum as SAEnum, ForeignKey, Uuid
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.chunk import Chunk
    from app.db.models.query_session import QuerySession


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
    session_id: UUID = Field(
        sa_column=Column(
            Uuid(),
            ForeignKey("query_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    filename: str
    content_type: str | None = None
    file_size_bytes: int | None = None
    status: DocumentStatus = Field(
        default=DocumentStatus.pending,
        sa_column=Column(
            SAEnum(
                DocumentStatus,
                values_callable=lambda enum: [item.value for item in enum],
                native_enum=False,
            ),
            nullable=False,
            server_default="pending",
        ),
    )
    error_message: str | None = None
    chunk_count: int = Field(default=0)
    token_count: int | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default="now()",
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default="now()",
        ),
    )

    session: "QuerySession" = Relationship(back_populates="documents")
    chunks: list["Chunk"] = Relationship(back_populates="document")
