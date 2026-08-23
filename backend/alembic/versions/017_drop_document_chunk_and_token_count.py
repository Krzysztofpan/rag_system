"""Drop unused documents.chunk_count and documents.token_count.

Revision ID: 017_drop_document_counts
Revises: 016_document_origin
Create Date: 2026-08-23

Chunk cardinality is len(chunks); per-chunk token length lives on chunks.
The document columns were denormalized copies that the API/UI did not use.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017_drop_document_counts"
down_revision: Union[str, Sequence[str], None] = "016_document_origin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("documents", "chunk_count")
    op.drop_column("documents", "token_count")


def downgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "chunk_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "documents",
        sa.Column("token_count", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE documents AS d
        SET
            chunk_count = COALESCE(c.n, 0),
            token_count = c.tokens
        FROM (
            SELECT
                document_id,
                COUNT(*) AS n,
                SUM(token_count) AS tokens
            FROM chunks
            GROUP BY document_id
        ) AS c
        WHERE d.id = c.document_id
        """
    )
