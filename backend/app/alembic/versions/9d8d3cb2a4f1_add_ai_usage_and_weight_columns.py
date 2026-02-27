"""add ai usage and weighted analysis columns

Revision ID: 9d8d3cb2a4f1
Revises: 7d26f2cf978a
Create Date: 2026-02-26 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9d8d3cb2a4f1"
down_revision: Union[str, Sequence[str], None] = "7d26f2cf978a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("criteria", sa.Column("weight", sa.Float(), nullable=True))
    op.execute("UPDATE criteria SET weight = 1.0 WHERE weight IS NULL")

    op.add_column("ai_analysis", sa.Column("strengths", sa.String(), nullable=True))
    op.add_column("ai_analysis", sa.Column("weaknesses", sa.String(), nullable=True))
    op.add_column(
        "ai_analysis",
        sa.Column("generated_by", sa.String(), nullable=False, server_default="ai"),
    )
    op.alter_column("ai_analysis", "generated_by", server_default=None)

    op.add_column("ai_usage_log", sa.Column("model_name", sa.String(), nullable=True))
    op.add_column("ai_usage_log", sa.Column("cost_amount", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("ai_usage_log", "cost_amount")
    op.drop_column("ai_usage_log", "model_name")

    op.drop_column("ai_analysis", "generated_by")
    op.drop_column("ai_analysis", "weaknesses")
    op.drop_column("ai_analysis", "strengths")

    op.drop_column("criteria", "weight")
