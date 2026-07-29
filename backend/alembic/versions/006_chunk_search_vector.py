"""Add search_vector tsvector column to chunks for Postgres FTS

Revision ID: 006_chunk_search_vector
Revises: 005_conversations
Create Date: 2026-07-29

Generated stored column from content + context (english config) + GIN index.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "006_chunk_search_vector"
down_revision: Union[str, Sequence[str], None] = "005_conversations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE chunks
        ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            to_tsvector(
                'english',
                coalesce(content, '') || ' ' || coalesce(context, '')
            )
        ) STORED
        """
    )
    op.execute(
        """
        CREATE INDEX idx_chunks_search
        ON chunks
        USING GIN (search_vector)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_chunks_search")
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS search_vector")
