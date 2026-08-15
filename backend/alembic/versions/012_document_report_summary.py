"""Add summary to document_reports

Revision ID: 012_document_report_summary
Revises: 011_backfill_source_count
Create Date: 2026-08-15

Stores an LLM-generated document summary on the report. Nullable because
it is filled in by a background task after ingest/reingest.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_document_report_summary"
down_revision: Union[str, Sequence[str], None] = "011_backfill_source_count"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_reports",
        sa.Column("summary", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_reports", "summary")
