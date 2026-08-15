"""Backfill conversations.source_count from documents

Revision ID: 011_backfill_source_count
Revises: 010_rename_conv_title
Create Date: 2026-08-08

Repairs denormalized source_count after it drifted from the real
document counts. Ongoing updates are handled in DocumentService.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "011_backfill_source_count"
down_revision: Union[str, Sequence[str], None] = "010_rename_conv_title"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
    pass
