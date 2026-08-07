"""Rename conversations.conversation_title to title

Revision ID: 010_rename_conv_title
Revises: 009_enable_rls
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op

revision: str = "010_rename_conv_title"
down_revision: Union[str, Sequence[str], None] = "009_enable_rls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "conversations",
        "conversation_title",
        new_column_name="title",
    )


def downgrade() -> None:
    op.alter_column(
        "conversations",
        "title",
        new_column_name="conversation_title",
    )
