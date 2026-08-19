"""Drop unused query_results observation tables

Revision ID: 014_drop_query_results
Revises: 013_create_messages
Create Date: 2026-08-19

query_results / query_result_chunks were created from the original RAG plan
(one query → retrieve → generate). Retrieval observability is LangSmith;
chat history is messages. The tables were empty and had no SQLModel models.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_drop_query_results"
down_revision: Union[str, Sequence[str], None] = "013_create_messages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("query_result_chunks")
    op.drop_table("query_results")


def downgrade() -> None:
    op.create_table(
        "query_results",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("rewritten_query", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column(
            "model",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'gpt-4o-mini'::text"),
        ),
        sa.Column(
            "iteration_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_query_results_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_query_results_conversation_id",
        "query_results",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "idx_query_results_created_at",
        "query_results",
        [sa.text("created_at DESC")],
        unique=False,
    )
    op.execute("ALTER TABLE query_results ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "query_result_chunks",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("query_result_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("similarity_score", sa.Double(), nullable=True),
        sa.Column("bm25_score", sa.Double(), nullable=True),
        sa.Column("final_score", sa.Double(), nullable=True),
        sa.Column("grade", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "grade IN ('yes', 'no', 'skipped')",
            name="query_result_chunks_grade_check",
        ),
        sa.ForeignKeyConstraint(
            ["query_result_id"],
            ["query_results.id"],
            name="query_result_chunks_query_result_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["chunks.id"],
            name="query_result_chunks_chunk_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_query_result_chunks_result_rank",
        "query_result_chunks",
        ["query_result_id", "rank"],
        unique=False,
    )
    op.execute("ALTER TABLE query_result_chunks ENABLE ROW LEVEL SECURITY")
