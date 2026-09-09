"""Create resources table.

Revision ID: 021_create_resources
Revises: 020_split_conversation_summaries
Create Date: 2026-09-04

Studio panel artifacts (notes, mind maps, …) belong to a conversation.
Type-specific payload lives in content JSONB; source document ids are a
plain uuid[] with no FK. An AFTER DELETE trigger on documents removes the
id from resources.documents_based_on. RLS enabled with no policies so
PostgREST anon/authenticated cannot read rows while the FastAPI postgres
role can.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "021_create_resources"
down_revision: Union[str, Sequence[str], None] = "020_split_conversation_summaries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "content",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("prompt_based_on", sa.Text(), nullable=True),
        sa.Column(
            "documents_based_on",
            postgresql.ARRAY(sa.Uuid()),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "type IN ('note', 'mind_map')",
            name="resources_type_check",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_resources_conversation_id",
        "resources",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "idx_resources_conversation_created_at",
        "resources",
        ["conversation_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.execute("ALTER TABLE resources ENABLE ROW LEVEL SECURITY")

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


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_prune_resource_documents_based_on ON documents"
    )
    op.execute("DROP FUNCTION IF EXISTS prune_resource_documents_based_on()")

    op.execute("ALTER TABLE resources DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "idx_resources_conversation_created_at",
        table_name="resources",
    )
    op.drop_index("idx_resources_conversation_id", table_name="resources")
    op.drop_table("resources")
