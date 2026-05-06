"""add mcq question options

Revision ID: 20260501mcqopts
Revises: c6ad943844ce
Create Date: 2026-05-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260501mcqopts"
down_revision: Union[str, Sequence[str], None] = "c6ad943844ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "questions",
        sa.Column(
            "question_type",
            sa.String(),
            nullable=False,
            server_default="single_choice",
        ),
    )
    op.add_column("questions", sa.Column("explanation", sa.Text(), nullable=True))

    op.create_table(
        "question_options",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("order_index", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            name="fk_question_options_question_id_questions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("answers", sa.Column("selected_option_id", sa.Uuid(), nullable=True))
    op.add_column("answers", sa.Column("text_answer", sa.Text(), nullable=True))
    op.add_column("answers", sa.Column("is_correct", sa.Boolean(), nullable=True))
    op.create_foreign_key(
        "fk_answers_selected_option_id_question_options",
        "answers",
        "question_options",
        ["selected_option_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_answers_selected_option_id_question_options",
        "answers",
        type_="foreignkey",
    )
    op.drop_column("answers", "is_correct")
    op.drop_column("answers", "text_answer")
    op.drop_column("answers", "selected_option_id")
    op.drop_table("question_options")
    op.drop_column("questions", "explanation")
    op.drop_column("questions", "question_type")
