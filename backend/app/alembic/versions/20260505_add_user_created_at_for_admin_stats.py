"""add user created at for admin stats

Revision ID: 20260505adminstats
Revises: 20260505attemptassignment
Create Date: 2026-05-05 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260505adminstats"
down_revision: Union[str, Sequence[str], None] = "20260505attemptassignment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "created_at")
