"""Store source origin on documents (file size / YouTube).

Revision ID: 016_document_origin
Revises: 015_conversation_memory_state
Create Date: 2026-08-23

facts about where a source came from live on documents.origin, not on
document_reports.quality. file_size_bytes moves into that JSONB.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "016_document_origin"
down_revision: Union[str, Sequence[str], None] = "015_conversation_memory_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("origin", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.execute(
        """
        UPDATE documents
        SET origin = jsonb_build_object(
            'kind', 'file',
            'file_size_bytes', file_size_bytes
        )
        WHERE file_size_bytes IS NOT NULL
        """
    )
    op.drop_column("documents", "file_size_bytes")


def downgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE documents
        SET file_size_bytes = (origin->>'file_size_bytes')::integer
        WHERE origin ? 'file_size_bytes'
        """
    )
    op.drop_column("documents", "origin")
