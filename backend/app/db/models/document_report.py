from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.document import Document


class DocumentReport(SQLModel, table=True):
    __tablename__ = "document_reports"

    document_id: UUID = Field(
        sa_column=Column(
            Uuid(),
            ForeignKey("documents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    parsed_content: str | None = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )
    summary: str | None = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )
    quality: Optional[dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default="now()",
        ),
    )

    document: "Document" = Relationship(back_populates="report")
