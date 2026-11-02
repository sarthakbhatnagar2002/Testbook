"""chapters

Revision ID: 9c42207ae744
Revises: 588ec57f6dc0
Create Date: 2026-11-02 14:09:35.482336

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c42207ae744'
down_revision: Union[str, Sequence[str], None] = '588ec57f6dc0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chapters",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("chapters_subject_idx", "chapters", ["subject_id"])

    with op.batch_alter_table("questions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("chapter_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "questions_chapter_id_fkey", "chapters", ["chapter_id"], ["id"], ondelete="CASCADE"
        )
    op.create_index("questions_chapter_idx", "questions", ["chapter_id"])


def downgrade() -> None:
    op.drop_index("questions_chapter_idx", table_name="questions")
    with op.batch_alter_table("questions", schema=None) as batch_op:
        batch_op.drop_constraint("questions_chapter_id_fkey", type_="foreignkey")
        batch_op.drop_column("chapter_id")

    op.drop_index("chapters_subject_idx", table_name="chapters")
    op.drop_table("chapters")
