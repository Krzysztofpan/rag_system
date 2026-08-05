from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Uuid
from sqlmodel import Field, Relationship, SQLModel

from app.db.models.auth_user import AuthUser  # noqa: F401

if TYPE_CHECKING:
    from app.db.models.document import Document


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
    conversation_title: str | None = Field(default=None)
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

    documents: list["Document"] = Relationship(back_populates="conversation")
