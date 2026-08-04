"""Add document_reports table for parsed content and quality

Revision ID: 007_document_reports
Revises: 006_chunk_search_vector
Create Date: 2026-08-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007_document_reports"
down_revision: Union[str, Sequence[str], None] = "006_chunk_search_vector"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_reports",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("parsed_content", sa.Text(), nullable=True),
        sa.Column("quality", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("document_id"),
    )


def downgrade() -> None:
    op.drop_table("document_reports")
