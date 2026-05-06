"""add user profile fields

Revision ID: 20260501userprof
Revises: 20260501qmodule
Create Date: 2026-05-01 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260501userprof"
down_revision: Union[str, Sequence[str], None] = "20260501qmodule"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("account_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("contact_email", sa.String(), nullable=True))
    op.add_column("users", sa.Column("contact_phone", sa.String(), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "contact_phone")
    op.drop_column("users", "contact_email")
    op.drop_column("users", "account_name")
