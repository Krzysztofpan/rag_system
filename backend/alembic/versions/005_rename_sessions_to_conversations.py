"""Rename query_sessions to conversations

Revision ID: 005_conversations
Revises: 004_query_sessions
Create Date: 2026-07-29

Renames domain terminology: session → conversation.
Also updates query_results.session_id → conversation_id for consistency.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "005_conversations"
down_revision: Union[str, Sequence[str], None] = "004_query_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("query_sessions", "conversations")

    op.execute(
        "ALTER TABLE conversations "
        "RENAME CONSTRAINT query_sessions_pkey TO conversations_pkey"
    )
    op.execute(
        "ALTER TABLE conversations "
        "RENAME CONSTRAINT fk_query_sessions_user_id_auth_users "
        "TO fk_conversations_user_id_auth_users"
    )
    op.execute(
        "ALTER INDEX idx_query_sessions_user_id "
        "RENAME TO idx_conversations_user_id"
    )
    op.execute(
        "ALTER INDEX idx_query_sessions_created_at "
        "RENAME TO idx_conversations_created_at"
    )

    op.alter_column("documents", "session_id", new_column_name="conversation_id")
    op.execute(
        "ALTER TABLE documents "
        "RENAME CONSTRAINT fk_documents_session_id_query_sessions "
        "TO fk_documents_conversation_id_conversations"
    )
    op.execute(
        "ALTER INDEX idx_documents_session_id "
        "RENAME TO idx_documents_conversation_id"
    )

    op.alter_column("query_results", "session_id", new_column_name="conversation_id")
    op.execute(
        "ALTER TABLE query_results "
        "RENAME CONSTRAINT query_results_session_id_fkey "
        "TO fk_query_results_conversation_id_conversations"
    )
    op.execute(
        "ALTER INDEX idx_query_results_session_id "
        "RENAME TO idx_query_results_conversation_id"
    )


def downgrade() -> None:
    op.execute(
        "ALTER INDEX idx_query_results_conversation_id "
        "RENAME TO idx_query_results_session_id"
    )
    op.execute(
        "ALTER TABLE query_results "
        "RENAME CONSTRAINT fk_query_results_conversation_id_conversations "
        "TO query_results_session_id_fkey"
    )
    op.alter_column("query_results", "conversation_id", new_column_name="session_id")

    op.execute(
        "ALTER INDEX idx_documents_conversation_id "
        "RENAME TO idx_documents_session_id"
    )
    op.execute(
        "ALTER TABLE documents "
        "RENAME CONSTRAINT fk_documents_conversation_id_conversations "
        "TO fk_documents_session_id_query_sessions"
    )
    op.alter_column("documents", "conversation_id", new_column_name="session_id")

    op.execute(
        "ALTER INDEX idx_conversations_created_at "
        "RENAME TO idx_query_sessions_created_at"
    )
    op.execute(
        "ALTER INDEX idx_conversations_user_id "
        "RENAME TO idx_query_sessions_user_id"
    )
    op.execute(
        "ALTER TABLE conversations "
        "RENAME CONSTRAINT fk_conversations_user_id_auth_users "
        "TO fk_query_sessions_user_id_auth_users"
    )
    op.execute(
        "ALTER TABLE conversations "
        "RENAME CONSTRAINT conversations_pkey TO query_sessions_pkey"
    )
    op.rename_table("conversations", "query_sessions")
