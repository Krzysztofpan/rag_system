"""Add topic to conversations

Revision ID: 019_conversation_topic
Revises: 018_message_sources
Create Date: 2026-08-27

Adds nullable text column `topic` on conversations.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "019_conversation_topic"
down_revision: Union[str, Sequence[str], None] = "018_message_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("topic", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversations", "topic")
