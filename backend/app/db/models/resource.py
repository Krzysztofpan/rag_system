from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, Column, DateTime, Enum as SAEnum, ForeignKey, Text, Uuid
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation


class ResourceType(str, Enum):
    note = "note"
    mind_map = "mind_map"


class Resource(SQLModel, table=True):
    __tablename__ = "resources"
    __table_args__ = (
        CheckConstraint(
            "type IN ('note', 'mind_map')",
            name="resources_type_check",
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
    type: ResourceType = Field(
        sa_column=Column(
            SAEnum(
                ResourceType,
                values_callable=lambda enum: [item.value for item in enum],
                native_enum=False,
            ),
            nullable=False,
        ),
    )
    title: str = Field(sa_column=Column(Text(), nullable=False))
    content: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    prompt_based_on: str | None = Field(
        default=None,
        sa_column=Column(Text(), nullable=True),
    )
    documents_based_on: list[UUID] = Field(
        default_factory=list,
        sa_column=Column(
            ARRAY(Uuid()),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
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
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default="now()",
        ),
    )

    conversation: "Conversation" = Relationship(back_populates="resources")
