"""Enable row level security on tables that were still exposed

Revision ID: 009_enable_rls
Revises: 008_conv_title_source_count
Create Date: 2026-08-06

Supabase publishes the `public` schema through its REST API, and the anon key
that reaches the browser can query it. Every table except these two already had
RLS on, so `document_reports` leaked parsed document content of all users.

No policies are created on purpose: the API talks to Postgres as `postgres`,
which bypasses RLS, so authorization stays in FastAPI while anon/authenticated
roles get nothing.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "009_enable_rls"
down_revision: Union[str, Sequence[str], None] = "008_conv_title_source_count"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("document_reports", "alembic_version")


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
