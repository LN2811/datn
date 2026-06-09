"""add curriculum module learning objectives

Revision ID: 20260603_module_objectives
Revises: aa1114ca1df0
Create Date: 2026-06-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260603_module_objectives"
down_revision: Union[str, None] = "aa1114ca1df0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "curriculum_modules",
        sa.Column("learning_objectives", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("curriculum_modules", "learning_objectives")
