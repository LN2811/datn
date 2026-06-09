"""add code review grading columns

Revision ID: 20260518codegrade
Revises: 9be1e64ab6b1
Create Date: 2026-05-18 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op


revision: str = "20260518codegrade"
down_revision: Union[str, Sequence[str], None] = "9be1e64ab6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "code_submissions",
        sa.Column("file_path", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "code_submissions",
        sa.Column("commit_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column("code_submissions", sa.Column("score", sa.Float(), nullable=True))
    op.add_column(
        "code_submissions",
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(),
            server_default="submitted",
            nullable=False,
        ),
    )
    op.add_column("code_submissions", sa.Column("graded_at", sa.DateTime(), nullable=True))

    op.add_column(
        "ai_code_feedback",
        sa.Column("code_quality_score", sa.Float(), nullable=True),
    )
    op.add_column("ai_code_feedback", sa.Column("logic_score", sa.Float(), nullable=True))
    op.add_column(
        "ai_code_feedback",
        sa.Column("performance_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "ai_code_feedback",
        sa.Column("strengths", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "ai_code_feedback",
        sa.Column("weaknesses", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "ai_code_feedback",
        sa.Column(
            "generated_by",
            sqlmodel.sql.sqltypes.AutoString(),
            server_default="ai",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("ai_code_feedback", "generated_by")
    op.drop_column("ai_code_feedback", "weaknesses")
    op.drop_column("ai_code_feedback", "strengths")
    op.drop_column("ai_code_feedback", "performance_score")
    op.drop_column("ai_code_feedback", "logic_score")
    op.drop_column("ai_code_feedback", "code_quality_score")

    op.drop_column("code_submissions", "graded_at")
    op.drop_column("code_submissions", "status")
    op.drop_column("code_submissions", "score")
    op.drop_column("code_submissions", "commit_hash")
    op.drop_column("code_submissions", "file_path")
