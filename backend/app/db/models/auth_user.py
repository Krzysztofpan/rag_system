"""Minimal mirror of Supabase Auth users for SQLAlchemy FK resolution.

The real table is owned by Supabase (`auth.users`). This model only registers
the table in metadata so `ForeignKey('auth.users.id')` resolves — do not
create/alter it via Alembic or the app.
"""

from uuid import UUID

from sqlmodel import Field, SQLModel


class AuthUser(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    id: UUID = Field(primary_key=True)
