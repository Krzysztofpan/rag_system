"""Store citation pointers on messages.

Revision ID: 018_message_sources
Revises: 017_drop_document_counts
Create Date: 2026-08-25

JSONB array of {index, kind, chunk_id|document_id|url}. Content stays in
chunks / reports / the remote URL — this column is only the [n] map.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "018_message_sources"
down_revision: Union[str, Sequence[str], None] = "017_drop_document_counts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "sources",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("messages", "sources")
