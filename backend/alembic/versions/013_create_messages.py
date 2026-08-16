"""Create messages table

Revision ID: 013_create_messages
Revises: 012_document_report_summary
Create Date: 2026-08-16

Chat messages belonging to a conversation. RLS is enabled with no policies
so the FastAPI postgres role can still access rows while anon/authenticated
keys cannot query the table through PostgREST.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_create_messages"
down_revision: Union[str, Sequence[str], None] = "012_document_report_summary"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')",
            name="messages_role_check",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_messages_conversation_id",
        "messages",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "idx_messages_conversation_created_at",
        "messages",
        ["conversation_id", sa.text("created_at ASC")],
        unique=False,
    )
    op.execute("ALTER TABLE messages ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE messages DISABLE ROW LEVEL SECURITY")
    op.drop_index("idx_messages_conversation_created_at", table_name="messages")
    op.drop_index("idx_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
