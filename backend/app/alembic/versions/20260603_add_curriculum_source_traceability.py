"""add curriculum source traceability

Revision ID: 20260603_source_trace
Revises: 20260603_module_objectives
Create Date: 2026-06-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260603_source_trace"
down_revision: Union[str, None] = "20260603_module_objectives"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("curriculums", sa.Column("source_coverage_score", sa.Float(), nullable=True))
    op.add_column("curriculums", sa.Column("heading_match_score", sa.Float(), nullable=True))
    op.add_column("curriculums", sa.Column("hallucination_score", sa.Float(), nullable=True))
    op.add_column("curriculum_modules", sa.Column("source_headings", sa.JSON(), nullable=True))
    op.add_column("curriculum_modules", sa.Column("source_chunks", sa.JSON(), nullable=True))
    op.add_column("curriculum_modules", sa.Column("heading_match_score", sa.Float(), nullable=True))
    op.add_column("curriculum_modules", sa.Column("hallucination_score", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("curriculum_modules", "hallucination_score")
    op.drop_column("curriculum_modules", "heading_match_score")
    op.drop_column("curriculum_modules", "source_chunks")
    op.drop_column("curriculum_modules", "source_headings")
    op.drop_column("curriculums", "hallucination_score")
    op.drop_column("curriculums", "heading_match_score")
    op.drop_column("curriculums", "source_coverage_score")
