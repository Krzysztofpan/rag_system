from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation


class ConversationSummary(SQLModel, table=True):
    __tablename__ = "conversation_summaries"

    conversation_id: UUID = Field(
        sa_column=Column(
            Uuid(),
            ForeignKey("conversations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    messages_summary: dict[str, object] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    documents_summary: str | None = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )
    compacted_through_message_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            Uuid(),
            ForeignKey("messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    version: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default="now()",
        ),
    )

    conversation: "Conversation" = Relationship(back_populates="summary_state")
