"""Unique chat-note pin per conversation message.

Revision ID: 023_unique_chat_note_message
Revises: 022_drop_resource_based_on
Create Date: 2026-09-08

A second Save in note on the same chat message must not insert another
row. Keep the earliest pin, then enforce uniqueness on
(conversation_id, content.message_id) for chat notes.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "023_unique_chat_note_message"
down_revision: Union[str, Sequence[str], None] = "022_drop_resource_based_on"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked AS (
          SELECT id,
                 ROW_NUMBER() OVER (
                   PARTITION BY conversation_id, content->>'message_id'
                   ORDER BY created_at ASC, id ASC
                 ) AS rn
          FROM resources
          WHERE type = 'note'
            AND content->>'kind' = 'chat'
            AND content->>'message_id' IS NOT NULL
        )
        DELETE FROM resources
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX idx_resources_chat_note_message
        ON resources (conversation_id, (content->>'message_id'))
        WHERE type = 'note'
          AND content->>'kind' = 'chat'
          AND content->>'message_id' IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_resources_chat_note_message")
