"""subject question banks, drop tests and roles

Revision ID: 588ec57f6dc0
Revises: ef5a27c95672
Create Date: 2026-10-28 10:56:06.037601

Full domain pivot: the app moves from teacher-authored timed tests to a
single-role practice question bank organized by subject. All test/exam
infrastructure is dropped. Existing questions and attempts are dropped and
recreated under the new shape rather than migrated field-by-field — they
were test/diagnostic content, not data worth preserving across this pivot.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "588ec57f6dc0"
down_revision: Union[str, Sequence[str], None] = "ef5a27c95672"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Test/exam infrastructure, no longer part of the app.
    op.drop_table("question_reports")
    op.drop_table("test_access")
    op.drop_table("test_questions")
    op.drop_table("test_attempts")
    op.drop_table("test_sections")
    op.drop_index("ix_tests_room_key", table_name="tests")
    op.drop_table("tests")

    op.drop_table("attempts")
    op.drop_table("options")
    op.drop_table("questions")

    op.create_table(
        "subjects",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "questions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("questions_subject_idx", "questions", ["subject_id"])

    op.create_table(
        "options",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("question_id", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("options_question_idx", "options", ["question_id"])

    op.create_table(
        "attempts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("question_id", sa.String(), nullable=False),
        sa.Column("selected_option_id", sa.String(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("attempts_user_question_idx", "attempts", ["user_id", "question_id"])
    op.create_index("attempts_question_idx", "attempts", ["question_id"])

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("role")


def downgrade() -> None:
    raise NotImplementedError(
        "This migration drops question/attempt data as part of a domain pivot; "
        "restore from a backup instead of downgrading."
    )
