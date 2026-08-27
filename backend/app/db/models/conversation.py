from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Uuid
from sqlmodel import Field, Relationship, SQLModel

from app.db.models.auth_user import AuthUser  # noqa: F401

if TYPE_CHECKING:
    from app.db.models.conversation_summary import ConversationSummary
    from app.db.models.document import Document
    from app.db.models.message import Message


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(
            Uuid(),
            ForeignKey("auth.users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    title: str | None = Field(default=None)
    topic: str | None = Field(default=None)
    source_count: int = Field(default=0)
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

    documents: list["Document"] = Relationship(
        back_populates="conversation",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    messages: list["Message"] = Relationship(
        back_populates="conversation",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    summary_state: Optional["ConversationSummary"] = Relationship(
        back_populates="conversation",
        sa_relationship_kwargs={
            "uselist": False,
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )
