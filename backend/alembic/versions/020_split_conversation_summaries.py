"""Split conversation summaries into documents and messages.

Revision ID: 020_split_conversation_summaries
Revises: 019_conversation_topic
Create Date: 2026-08-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "020_split_conversation_summaries"
down_revision: Union[str, Sequence[str], None] = "019_conversation_topic"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "conversation_summaries",
        "summary",
        new_column_name="messages_summary",
    )
    op.alter_column(
        "conversation_summaries",
        "messages_summary",
        existing_type=postgresql.JSONB(),
        nullable=True,
    )
    op.add_column(
        "conversation_summaries",
        sa.Column("documents_summary", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversation_summaries", "documents_summary")
    op.execute(
        "UPDATE conversation_summaries "
        "SET messages_summary = '{}'::jsonb "
        "WHERE messages_summary IS NULL"
    )
    op.alter_column(
        "conversation_summaries",
        "messages_summary",
        existing_type=postgresql.JSONB(),
        nullable=False,
    )
    op.alter_column(
        "conversation_summaries",
        "messages_summary",
        new_column_name="summary",
    )
