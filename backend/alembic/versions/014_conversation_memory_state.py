"""Add conversation memory state.

Revision ID: 014_conversation_memory_state
Revises: 013_create_messages
Create Date: 2026-08-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014_conversation_memory_state"
down_revision: Union[str, Sequence[str], None] = "013_create_messages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_summaries",
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("summary", postgresql.JSONB(), nullable=False),
        sa.Column("compacted_through_message_id", sa.Uuid(), nullable=True),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["compacted_through_message_id"],
            ["messages.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("conversation_id"),
    )
    op.execute("ALTER TABLE conversation_summaries ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE conversation_summaries DISABLE ROW LEVEL SECURITY")
    op.drop_table("conversation_summaries")
