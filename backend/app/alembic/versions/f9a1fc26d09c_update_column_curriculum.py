"""update column curriculum

Revision ID: f9a1fc26d09c
Revises: 9d8d3cb2a4f1
Create Date: 2026-04-21 21:46:19.555041

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9a1fc26d09c'
down_revision: Union[str, Sequence[str], None] = '9d8d3cb2a4f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "curriculum_modules",
        sa.Column("content", sa.String(), nullable=True),
    )
    op.add_column(
        "curriculum_modules",
        sa.Column(
            "generate_status",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "curriculum_modules",
        sa.Column(
            "is_preview",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "curriculums",
        sa.Column("total_module", sa.Integer(), nullable=True),
    )
    op.add_column(
        "curriculums",
        sa.Column(
            "ready_module",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("curriculums", "ready_module")
    op.drop_column("curriculums", "total_module")
    op.drop_column("curriculum_modules", "is_preview")
    op.drop_column("curriculum_modules", "generate_status")
    op.drop_column("curriculum_modules", "content")
