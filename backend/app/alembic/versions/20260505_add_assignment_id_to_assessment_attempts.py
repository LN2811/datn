"""add assignment id to assessment attempts

Revision ID: 20260505attemptassignment
Revises: 20260501userprof
Create Date: 2026-05-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260505attemptassignment"
down_revision: Union[str, Sequence[str], None] = "20260501userprof"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "assessment_attempts",
        sa.Column("assignment_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_assessment_attempts_assignment_id_assignments",
        "assessment_attempts",
        "assignments",
        ["assignment_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_assessment_attempts_assignment_id_assignments",
        "assessment_attempts",
        type_="foreignkey",
    )
    op.drop_column("assessment_attempts", "assignment_id")
