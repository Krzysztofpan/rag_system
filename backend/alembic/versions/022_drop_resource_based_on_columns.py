"""Drop resources.prompt_based_on and documents_based_on.

Revision ID: 022_drop_resource_based_on
Revises: 021_create_resources
Create Date: 2026-09-05

Source provenance columns are unused; remove them and the documents
DELETE trigger that pruned documents_based_on.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "022_drop_resource_based_on"
down_revision: Union[str, Sequence[str], None] = "021_create_resources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_prune_resource_documents_based_on ON documents"
    )
    op.execute("DROP FUNCTION IF EXISTS prune_resource_documents_based_on()")
    op.drop_column("resources", "prompt_based_on")
    op.drop_column("resources", "documents_based_on")


def downgrade() -> None:
    op.add_column(
        "resources",
        sa.Column(
            "documents_based_on",
            postgresql.ARRAY(sa.Uuid()),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
    )
    op.add_column(
        "resources",
        sa.Column("prompt_based_on", sa.Text(), nullable=True),
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prune_resource_documents_based_on()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          UPDATE resources
          SET documents_based_on = array_remove(documents_based_on, OLD.id)
          WHERE OLD.id = ANY(documents_based_on);
          RETURN OLD;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_prune_resource_documents_based_on
        AFTER DELETE ON documents
        FOR EACH ROW
        EXECUTE FUNCTION prune_resource_documents_based_on()
        """
    )
