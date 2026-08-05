"""Add conversation_title and source_count to conversations

Revision ID: 008_conv_title_source_count
Revises: 007_document_reports
Create Date: 2026-08-05

Adds denormalized listing fields on conversations:
- conversation_title (nullable text)
- source_count (non-null int, backfilled from documents)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_conv_title_source_count"
down_revision: Union[str, Sequence[str], None] = "007_document_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("conversation_title", sa.Text(), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "source_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.execute(
        """
        UPDATE conversations AS c
        SET source_count = (
            SELECT COUNT(*)::integer
            FROM documents AS d
            WHERE d.conversation_id = c.id
        )
        """
    )


def downgrade() -> None:
    op.drop_column("conversations", "source_count")
    op.drop_column("conversations", "conversation_title")
