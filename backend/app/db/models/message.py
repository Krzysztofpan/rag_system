from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, Column, DateTime, Enum as SAEnum, ForeignKey, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"


class Message(SQLModel, table=True):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="messages_role_check",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    conversation_id: UUID = Field(
        sa_column=Column(
            Uuid(),
            ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    text: str = Field(sa_column=Column(sa.Text(), nullable=False))
    role: MessageRole = Field(
        sa_column=Column(
            SAEnum(
                MessageRole,
                values_callable=lambda enum: [item.value for item in enum],
                native_enum=False,
            ),
            nullable=False,
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default="now()",
        ),
    )
    sources: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    conversation: "Conversation" = Relationship(back_populates="messages")
