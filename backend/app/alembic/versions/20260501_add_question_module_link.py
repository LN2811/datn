"""add question module link

Revision ID: 20260501qmodule
Revises: 20260501mcqopts
Create Date: 2026-05-01 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260501qmodule"
down_revision: Union[str, Sequence[str], None] = "20260501mcqopts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("questions", sa.Column("curriculum_module_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_questions_curriculum_module_id_curriculum_modules",
        "questions",
        "curriculum_modules",
        ["curriculum_module_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_questions_curriculum_module_id_curriculum_modules",
        "questions",
        type_="foreignkey",
    )
    op.drop_column("questions", "curriculum_module_id")
