"""Add optional context column to chunks

Revision ID: 002_chunk_context
Revises: 001_initial
Create Date: 2026-07-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_chunk_context"
down_revision: Union[str, Sequence[str], None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("context", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("chunks", "context")
