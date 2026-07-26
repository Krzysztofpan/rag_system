"""Replace chunks.page with pages integer array

Revision ID: 003_chunk_pages_array
Revises: 002_chunk_context
Create Date: 2026-07-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_chunk_pages_array"
down_revision: Union[str, Sequence[str], None] = "002_chunk_context"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chunks",
        sa.Column("pages", postgresql.ARRAY(sa.Integer()), nullable=True),
    )
    op.execute(
        """
        UPDATE chunks
        SET pages = ARRAY[page]
        WHERE page IS NOT NULL
        """
    )
    op.drop_column("chunks", "page")


def downgrade() -> None:
    op.add_column("chunks", sa.Column("page", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE chunks
        SET page = pages[1]
        WHERE pages IS NOT NULL AND cardinality(pages) > 0
        """
    )
    op.drop_column("chunks", "pages")
