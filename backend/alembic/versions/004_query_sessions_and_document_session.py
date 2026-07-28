"""Add query_sessions.user_id and documents.session_id

Revision ID: 004_query_sessions
Revises: 003_chunk_pages_array
Create Date: 2026-07-28

`query_sessions` may already exist (created from earlier plan SQL without
user_id). This migration alters it in place, then links documents to sessions.

Existing documents without a session are removed (dev-stage cleanup) so
session_id can be NOT NULL.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_query_sessions"
down_revision: Union[str, Sequence[str], None] = "003_chunk_pages_array"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names(schema="public"))

    if "query_sessions" not in tables:
        op.create_table(
            "query_sessions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
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
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["auth.users.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        columns = {col["name"] for col in inspector.get_columns("query_sessions")}
        if "user_id" not in columns:
            # Empty/orphan sessions cannot be owned; wipe before NOT NULL.
            op.execute("DELETE FROM query_sessions")
            op.add_column(
                "query_sessions",
                sa.Column("user_id", sa.Uuid(), nullable=False),
            )
            op.create_foreign_key(
                "fk_query_sessions_user_id_auth_users",
                "query_sessions",
                "users",
                ["user_id"],
                ["id"],
                source_schema="public",
                referent_schema="auth",
                ondelete="CASCADE",
            )

    existing_indexes = {
        idx["name"] for idx in inspector.get_indexes("query_sessions")
    }
    if "idx_query_sessions_user_id" not in existing_indexes:
        op.create_index(
            "idx_query_sessions_user_id",
            "query_sessions",
            ["user_id"],
            unique=False,
        )
    if "idx_query_sessions_created_at" not in existing_indexes:
        op.create_index(
            "idx_query_sessions_created_at",
            "query_sessions",
            [sa.text("created_at DESC")],
            unique=False,
        )

    # Orphan documents cannot be mapped to a session; wipe before NOT NULL FK.
    op.execute("DELETE FROM chunks")
    op.execute("DELETE FROM documents")

    doc_columns = {col["name"] for col in inspector.get_columns("documents")}
    if "session_id" not in doc_columns:
        op.add_column(
            "documents",
            sa.Column("session_id", sa.Uuid(), nullable=False),
        )
        op.create_foreign_key(
            "fk_documents_session_id_query_sessions",
            "documents",
            "query_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index(
            "idx_documents_session_id",
            "documents",
            ["session_id"],
            unique=False,
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    doc_indexes = {idx["name"] for idx in inspector.get_indexes("documents")}
    if "idx_documents_session_id" in doc_indexes:
        op.drop_index("idx_documents_session_id", table_name="documents")

    doc_fks = {fk["name"] for fk in inspector.get_foreign_keys("documents")}
    if "fk_documents_session_id_query_sessions" in doc_fks:
        op.drop_constraint(
            "fk_documents_session_id_query_sessions",
            "documents",
            type_="foreignkey",
        )

    doc_columns = {col["name"] for col in inspector.get_columns("documents")}
    if "session_id" in doc_columns:
        op.drop_column("documents", "session_id")

    session_indexes = {
        idx["name"] for idx in inspector.get_indexes("query_sessions")
    }
    if "idx_query_sessions_created_at" in session_indexes:
        op.drop_index(
            "idx_query_sessions_created_at", table_name="query_sessions"
        )
    if "idx_query_sessions_user_id" in session_indexes:
        op.drop_index("idx_query_sessions_user_id", table_name="query_sessions")

    session_fks = {
        fk["name"] for fk in inspector.get_foreign_keys("query_sessions")
    }
    if "fk_query_sessions_user_id_auth_users" in session_fks:
        op.drop_constraint(
            "fk_query_sessions_user_id_auth_users",
            "query_sessions",
            type_="foreignkey",
        )

    session_columns = {
        col["name"] for col in inspector.get_columns("query_sessions")
    }
    if "user_id" in session_columns:
        op.drop_column("query_sessions", "user_id")
